#!/bin/bash

source /mnt/utils.sh

if [ -z "$CLUSTER_HOST" ] || [ -z "$CLUSTER_USER" ] || [ -z "$CLUSTER_PASSWORD" ] || [ -z "$DISTRIBUTION_VERSION" ]; then
    echo "Please set the CLUSTER_HOST, CLUSTER_USER, CLUSTER_PASSWORD and DISTRIBUTION_VERSION environment variables"
    exit 1
fi

# This comes from the user `terraform.tfvars` configuration file
# shellcheck disable=SC2154
SNAPSHOT_S3_BUCKET="${s3_bucket_name}"

# This comes from the user `terraform.tfvars` configuration file
# shellcheck disable=SC2154
SNAPSHOT_VERSION="${snapshot_version}"

# This comes from the user `terraform.tfvars` configuration file
# shellcheck disable=SC2154
WORKLOAD="$${WORKLOAD:-${workload}}"
WORKLOAD_PARAMS=/mnt/workload_params.json

# Based on the workload, we can figure out the index name. It is mostly the same, but somtimes not.
INDEX_NAME=$(workload_index_name $WORKLOAD)

CLIENT_OPTIONS=$(join_by , "basic_auth_user:$CLUSTER_USER,basic_auth_password:$CLUSTER_PASSWORD,use_ssl:true,verify_certs:false" $EXTRA_CLIENT_OPTIONS)
SNAPSHOT_NAME=$(snapshot_name "$WORKLOAD;no-force-merge-1" "$WORKLOAD_PARAMS")

INGESTION_RESULTS=/mnt/ingestion_results
USER_TAGS="run-type:ingest,aws-user-id:$AWS_USERID,ci:$(ci_tag_value)"

# If the snapshot already exists, skip ingestion (check response.total > 0),
# unless FORCE_INGESTION is set
echo "Checking if snapshot already exists..."
register_snapshot_repo \
  "$CLUSTER_HOST" \
  "$CLUSTER_USER" \
  "$CLUSTER_PASSWORD" \
  "$SNAPSHOT_S3_BUCKET" \
  "$ENGINE_TYPE" \
  "$CLUSTER_VERSION" \
  "$WORKLOAD" \
  "$SNAPSHOT_VERSION"

response=$(curl -s -ku $CLUSTER_USER:$CLUSTER_PASSWORD -X GET "$CLUSTER_HOST/_snapshot/$SNAPSHOT_S3_BUCKET/$SNAPSHOT_NAME")
if [[ $(echo "$response" | jq -r '.snapshots | length') -gt 0 ]] && [ -z "$FORCE_INGESTION" ]; then
    echo "There's a snapshot already. Use /mnt/restore_snapshot.sh to restore it."
    echo "If you want to recreate the snapshot, set FORCE_INGESTION=true."
    exit 1
fi

version_gte() {
    # Test if version $1 is greater than or equal to version $2
    [ "$(echo -e "$1\n$2" | sort -V | head -n1)" == "$2" ]
}

# Modify vectorsearch index settings for OS >=2.18.0 nmslib and faiss
if version_gte "$CLUSTER_VERSION" "2.18.0";  then
  sed -i 's/"knn": true$/"knn": true,\n        "knn.advanced.approximate_threshold": 0/' \
    /mnt/.benchmark/benchmarks/workloads/default/vectorsearch/indices/faiss-index.json \
    /mnt/.benchmark/benchmarks/workloads/default/vectorsearch/indices/nmslib-index.json
  echo "Set index.knn.advanced.approximate_threshold to 0"
fi

EXCLUDE_TASKS="type:search,prod-queries,warmup-indices"

# Ingest data in the cluster
opensearch-benchmark execute-test \
    --pipeline=benchmark-only \
    --workload=$WORKLOAD \
    --target-hosts="$CLUSTER_HOST" \
    --workload-params="$WORKLOAD_PARAMS" \
    --client-options="$CLIENT_OPTIONS" \
    --kill-running-processes \
    --results-file=$INGESTION_RESULTS \
    --test-execution-id=ingestion \
    --distribution-version=$DISTRIBUTION_VERSION \
    --test-procedure=no-train-test-index-only \
    --user-tag="$USER_TAGS" \
    --telemetry="node-stats"

# Lets complete a refresh
echo "Doing a Flush to commit all the segments"
curl -s -ku $CLUSTER_USER:$CLUSTER_PASSWORD -X POST "$CLUSTER_HOST/$INDEX_NAME/_flush"

echo "Doing a Refresh after flush"
curl -s -ku $CLUSTER_USER:$CLUSTER_PASSWORD -X POST "$CLUSTER_HOST/$INDEX_NAME/_refresh"

echo "Sleeping for 30 sec before we can fetch the merge stats"
sleep 30
echo "Getting merge stats"
while true
do
  # gather all the merge stats
  merge_stats=$(curl -s -ku $CLUSTER_USER:$CLUSTER_PASSWORD -X GET "$CLUSTER_HOST/_nodes/stats?filter_path=nodes.*.indices.merges&format=json")
  # Find the current state of the merges
  current_merges=$(echo "$merge_stats" | jq -r '.nodes | to_entries[] | .value.indices.merges | .current')

  all_merges_completed=1
  for i in $current_merges; do
    echo "Current merges: $i"
    if [ "$i" -gt 0 ]; then
      echo "Merges are still in progress, waiting for them to finish. Sleeping for 30 sec"
      all_merges_completed=0
      break
    fi
  done

  if [ $all_merges_completed -eq 1 ]; then
    echo "All merges are completed. Exiting from the loop"
    break
  fi
  echo "Merges are still in progress, waiting for them to finish. Sleeping for 30 sec"
  sleep 30
done

echo "Doing a final refresh before taking a snapshot"
curl -s -ku $CLUSTER_USER:$CLUSTER_PASSWORD -X POST "$CLUSTER_HOST/$INDEX_NAME/_refresh"

check_params "$CLUSTER_USER" "$CLUSTER_PASSWORD" "$CLUSTER_HOST" "$WORKLOAD" "$INDEX_NAME"

# If SNAPSHOT_S3_BUCKET is not set, skip the snapshot
if [ -z "$SNAPSHOT_S3_BUCKET" ]; then
    echo "Skipping snapshot"
    exit 0
fi

# Delete the snapshot if it already exists
echo "Deleting snapshot..."
curl -s -ku $CLUSTER_USER:$CLUSTER_PASSWORD -X DELETE "$CLUSTER_HOST/_snapshot/$SNAPSHOT_S3_BUCKET/$SNAPSHOT_NAME"
echo "Snapshot deletion initiated, waiting for confirmation"
while true
do
  curl -s --max-time 5 -ku "$CLUSTER_USER:$CLUSTER_PASSWORD" "$CLUSTER_HOST"/_snapshot/$SNAPSHOT_S3_BUCKET/$SNAPSHOT_NAME | jq -e ".error" && break
  sleep 1
done
echo "Snapshot deleted"

# Perform the snapshot
echo "Performing snapshot..."
response=$(curl -ku $CLUSTER_USER:$CLUSTER_PASSWORD -X PUT "$CLUSTER_HOST/_snapshot/$SNAPSHOT_S3_BUCKET/$SNAPSHOT_NAME?wait_for_completion=true" -H "Content-Type: application/json" -d"
{
  \"indices\": \"$INDEX_NAME\"
}")
echo "$response" | jq -e '.error' > /dev/null && {
  echo "Error in response from Elasticsearch"
  echo "$response"
  exit 4
}
echo "Snapshot done"

bash /mnt/restore_snapshot.sh
