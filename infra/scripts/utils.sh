#!/usr/bin/env bash

get_doc_count() {
    local workload=$1

    declare -A doc_counts
    doc_counts["big5"]=116000000
    doc_counts["nyc_taxis"]=165346691 # NOTE: should be 165346692 but there's an issue with one document
    doc_counts["pmc"]=574199
    doc_counts["noaa"]=33659481

    # Check if the workload exists in the associative array
    if [[ -v "doc_counts[$workload]" ]]; then
        # Get the DOC_COUNT based on the WORKLOAD
        echo "${doc_counts[$workload]}"
    else
        # Default value
        echo "1000"
    fi
}

get_shards_count() {
    local workload=$1

    declare -A shards_count
    shards_count["big5"]=1
    shards_count["pmc"]=5

    # Check if the workload exists in the associative array
    if [[ -v "shards_count[$workload]" ]]; then
        # Get the DOC_COUNT based on the WORKLOAD
        echo "${shards_count[$workload]}"
    else
        # Default value
        echo "1"
    fi
}

check_value () {
    local name=$1
    local expected=$2
    local actual=$3

    if [[ "$expected" != "$actual" ]]; then
        printf 'Incorrect %s value, expected %s, actual %s\n' "$name" "$expected" "$actual"
        exit 1
    fi
}

check_params () {
    local user=$1
    local password=$2
    local host=$3
    local workload=$4
    local index=$5

    read -r doc_count shards_total shards_failed shards_skipped < <( \
        curl \
            --silent \
            --insecure \
            --user "$user:$password" \
            --request GET "$host/$index/_count" \
        | jq --raw-output '"\(.count) \(._shards.total) \(._shards.failed) \(._shards.skipped)"' \
    )

    check_value "document count" "${DOC_COUNT:-$(get_doc_count $workload)}" "$doc_count"
    check_value "total shards count" "${TOTAL_SHARDS:-$(get_shards_count $workload)}" "$shards_total"
    check_value "failed shards count" "${FAILED_SHARDS:-0}" "$shards_failed"
    check_value "skipped shards count" "${SKIPPED_SHARDS:-0}" "$shards_skipped"
}


# Uses opensearch benchmark to get the index names. Note, this will use the default invocation params.
workload_index_name() {
    cat <<EOF | python3 2>/dev/null | tail -n1
import logging
logger = logging.getLogger()
logger.disabled = True
import osbenchmark, osbenchmark.config, osbenchmark.paths, osbenchmark.workload
cfg = osbenchmark.config.Config()
cfg.load_config()
cfg.add(osbenchmark.config.Scope.applicationOverride, "workload", "workload.name", "$1")
cfg.add(osbenchmark.config.Scope.applicationOverride, "workload", "repository.name", "default")
cfg.add(osbenchmark.config.Scope.applicationOverride, "system", "offline.mode", "False")
cfg.add(osbenchmark.config.Scope.applicationOverride, "node", "benchmark.root", osbenchmark.paths.benchmark_root())
wl = osbenchmark.workload.load_workload(cfg)
print(wl.indices[0].name)
logger.disabled = False
EOF
}


# Helper function to join parameters by single charater delimiter
join_by() {
    local IFS="$1";
    shift;
    echo "$*";
}

snapshot_name() {
    workload_name=$1
    workload_params=$2

    # Sort the params alphabetically
    sorted_params=$(IFS=,; echo "$workload_params" | tr ',' '\n' | sort | tr '\n' ',')
    # Remove the last ','
    sorted_params=${sorted_params%,}
    # Join the workload name and sorted params with `;` and md5sum it (return only the hash)
    echo "$workload_name;$sorted_params" | md5sum | cut -d' ' -f1
}

register_snapshot_repo() {
    local cluster_host=$1
    local cluster_user=$2
    local cluster_password=$3
    local snapshot_s3_bucket=$4
    local cluster_type=$5
    local cluster_version=$6
    local workload=$7

    # Register the S3 repository for snapshots (same for OS/ES)
    echo "Registering snapshot repository..."
    response=$(curl -s -ku $cluster_user:$cluster_password -X PUT "$cluster_host/_snapshot/$snapshot_s3_bucket?pretty" -H 'Content-Type: application/json' -d"
{
  \"type\": \"s3\",
  \"settings\": {
    \"bucket\": \"$snapshot_s3_bucket\",
    \"base_path\": \"$cluster_type/$cluster_version/$workload\"
  }
}
")
    echo "$response" | jq -e '.error' > /dev/null && {
        echo "Error in response from Elasticsearch"
        echo "$response"
        exit 3
    }
}

benchmark_single() {
    workload=$1
    cluster_host=$2
    workload_params=$3
    client_options=$4
    results_file=$5
    test_execution_id=$6
    test_procedure=$7
    distribution_version=$8
    user_tags=$9

    opensearch-benchmark execute-test \
        --pipeline=benchmark-only \
        --workload=$workload  \
        --target-hosts="$cluster_host" \
        --workload-params="$workload_params" \
        --client-options="$client_options" \
        --kill-running-processes \
        --include-tasks="type:search" \
        --results-file="$results_file" \
        --test-execution-id="$test_execution_id" \
        --test-procedure="$test_procedure" \
        --distribution-version=$distribution_version \
        --user-tag="$user_tags" \
        --telemetry="node-stats"
}
