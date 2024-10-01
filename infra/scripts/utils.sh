#!/usr/bin/env bash

get_doc_count() {
    local workload=$1

    declare -A doc_counts
    doc_counts["big5"]=116000000
    doc_counts["nyc_taxis"]=165346692
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
