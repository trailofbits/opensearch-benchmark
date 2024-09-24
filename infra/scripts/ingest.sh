#!/bin/bash

source /utils.sh

if [ -z "$CLUSTER_HOST" ] || [ -z "$CLUSTER_USER" ] || [ -z "$CLUSTER_PASSWORD" ] || [ -z "$CLUSTER_VERSION" ]; then
    echo "Please set the CLUSTER_HOST, CLUSTER_USER, CLUSTER_PASSWORD and CLUSTER_VERSION environment variables"
    exit 1
fi

# This comes from the user `terraform.tfvars` configuration file
# shellcheck disable=SC2154
SNAPSHOT_S3_BUCKET="${s3_bucket_name}"

# This comes from the user `terraform.tfvars` configuration file
# shellcheck disable=SC2154
WORKLOAD="${workload}"

# This comes from the user `terraform.tfvars` configuration file
# shellcheck disable=SC2154
WORKLOAD_PARAMS="${workload_params}"

CLIENT_OPTIONS="basic_auth_user:$CLUSTER_USER,basic_auth_password:$CLUSTER_PASSWORD,use_ssl:true,verify_certs:false"
SNAPSHOT_NAME=$(echo "$WORKLOAD;$WORKLOAD_PARAMS" | md5sum | cut -d' ' -f1)

INGESTION_RESULTS=/mnt/ingestion_results
USER_TAGS="run-type:ingest"

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
    --distribution-version=$CLUSTER_VERSION \
    --exclude-tasks="type:search" \
    --user-tag="$USER_TAGS" \
    --telemetry="node-stats"

check_params "$CLUSTER_USER" "$CLUSTER_PASSWORD" "$CLUSTER_HOST" "$WORKLOAD"

# If SNAPSHOT_S3_BUCKET is not set, skip the snapshot
if [ -z "$SNAPSHOT_S3_BUCKET" ]; then
    echo "Skipping snapshot"
    exit 0
fi

# Register the S3 repository for snapshots (same for OS/ES)
response=$(curl -s -ku $CLUSTER_USER:$CLUSTER_PASSWORD -X PUT "$CLUSTER_HOST/_snapshot/$SNAPSHOT_S3_BUCKET?pretty" -H 'Content-Type: application/json' -d"
{
  \"type\": \"s3\",
  \"settings\": {
    \"bucket\": \"$SNAPSHOT_S3_BUCKET\"
  }
}
")
echo "$response" | jq -e '.error' > /dev/null && {
  echo "Error in response from Elasticsearch"
  echo "$response"
  exit 3
}

# Perform the snapshot
response=$(curl -ku $CLUSTER_USER:$CLUSTER_PASSWORD -X PUT "$CLUSTER_HOST/_snapshot/$SNAPSHOT_S3_BUCKET/$SNAPSHOT_NAME" -H "Content-Type: application/json" -d"
{
  \"indices\": \"$WORKLOAD\"
}")
echo "$response" | jq -e '.error' > /dev/null && {
  echo "Error in response from Elasticsearch"
  echo "$response"
  exit 4
}

# Wait until the snapshot is in SUCCESS state
while true; do
  STATUS=$(curl -s -ku $CLUSTER_USER:$CLUSTER_PASSWORD -X GET "$CLUSTER_HOST/_snapshot/$SNAPSHOT_S3_BUCKET/$SNAPSHOT_NAME/_status?pretty" | jq -r '.snapshots[0].state')
  if [ "$STATUS" == "SUCCESS" ]; then
    break
  fi
  echo "Snapshot status: $STATUS, waiting for it to be SUCCESS"
  sleep 5
done

# Restore the snapshot
curl -ku $CLUSTER_USER:$CLUSTER_PASSWORD -X DELETE "$CLUSTER_HOST/$WORKLOAD?pretty"
curl -ku $CLUSTER_USER:$CLUSTER_PASSWORD -X POST "$CLUSTER_HOST/_snapshot/$SNAPSHOT_S3_BUCKET/$SNAPSHOT_NAME/_restore" -H "Content-Type: application/json" -d"
{
  \"indices\": \"$WORKLOAD\"
}"

# Wait until the restore is complete (stage == "DONE")
# Do not fail if the curl|jq command fails for any reasons
while [ "$(curl -s -ku $CLUSTER_USER:$CLUSTER_PASSWORD "$CLUSTER_HOST/_recovery" | jq -r ".[\"$WORKLOAD\"][\"shards\"] | .[].stage" | sort | uniq)" != "DONE" ]; do
  echo "Waiting for restore to complete"
  sleep 10
done
echo "Snapshot restore completed"

check_params "$CLUSTER_USER" "$CLUSTER_PASSWORD" "$CLUSTER_HOST" "$WORKLOAD"
