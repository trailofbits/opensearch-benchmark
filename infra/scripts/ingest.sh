#!/bin/bash

source /utils.sh

if [ -z "$CLUSTER_HOST" ] || [ -z "$CLUSTER_USER" ] || [ -z "$CLUSTER_PASSWORD" ] || [ -z "$CLUSTER_VERSION" ]; then
    echo "Please set the CLUSTER_HOST, CLUSTER_USER, CLUSTER_PASSWORD and CLUSTER_VERSION environment variables"
    exit 1
fi

SNAPSHOT_S3_BUCKET=${s3_bucket_name}
WORKLOAD="${workload}"
WORKLOAD_PARAMS=${workload_params}
CLIENT_OPTIONS="basic_auth_user:$CLUSTER_USER,basic_auth_password:$CLUSTER_PASSWORD,use_ssl:true,verify_certs:false"
SNAPSHOT_NAME=$(echo "$WORKLOAD;$WORKLOAD_PARAMS" | md5sum | cut -d' ' -f1)

INGESTION_RESULTS=/mnt/ingestion_results

# If the snapshot already exists, skip ingestion (check response.total > 0),
# unless FORCE_INGESTION is set
response=$(curl -s -ku $CLUSTER_USER:$CLUSTER_PASSWORD -X GET "$CLUSTER_HOST/_snapshot/$SNAPSHOT_S3_BUCKET/$SNAPSHOT_NAME")
if [[ $(echo "$response" | jq -r '.total') -gt 0 ]] && [ -z "$FORCE_INGESTION" ]; then
    echo "There's a snapshot already. Use /restore_snapshot.sh to restore it."
    echo "If you want to recreate the snapshot, set FORCE_INGESTION=true."
    exit 1
fi

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
    --exclude-tasks="type:search"

check_params "$CLUSTER_USER" "$CLUSTER_PASSWORD" "$CLUSTER_HOST" "$WORKLOAD"

# If SNAPSHOT_S3_BUCKET is not set, skip the snapshot
if [ -z "$SNAPSHOT_S3_BUCKET" ]; then
    echo "Skipping snapshot"
    exit 0
fi

# Register the S3 repository for snapshots (same for OS/ES)
echo "Registering snapshot repository..."
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

# Delete the snapshot if it already exists
echo "Deleting snapshot..."
curl -s -ku $CLUSTER_USER:$CLUSTER_PASSWORD -X DELETE "$CLUSTER_HOST/_snapshot/$SNAPSHOT_S3_BUCKET/$SNAPSHOT_NAME?wait_for_completion=true"
echo "Snapshot deleted"

# Perform the snapshot
echo "Performing snapshot..."
response=$(curl -ku $CLUSTER_USER:$CLUSTER_PASSWORD -X PUT "$CLUSTER_HOST/_snapshot/$SNAPSHOT_S3_BUCKET/$SNAPSHOT_NAME?wait_for_completion=true" -H "Content-Type: application/json" -d"
{
  \"indices\": \"$WORKLOAD\"
}")
echo "$response" | jq -e '.error' > /dev/null && {
  echo "Error in response from Elasticsearch"
  echo "$response"
  exit 4
}
echo "Snapshot done"

# Restore the snapshot
echo "Restoring snapshot..."
curl -ku $CLUSTER_USER:$CLUSTER_PASSWORD -X DELETE "$CLUSTER_HOST/$WORKLOAD?pretty"
curl -ku $CLUSTER_USER:$CLUSTER_PASSWORD -X POST "$CLUSTER_HOST/_snapshot/$SNAPSHOT_S3_BUCKET/$SNAPSHOT_NAME/_restore?wait_for_completion=true" -H "Content-Type: application/json" -d"
{
  \"indices\": \"$WORKLOAD\"
}"
echo "Snapshot restored"

check_params "$CLUSTER_USER" "$CLUSTER_PASSWORD" "$CLUSTER_HOST" "$WORKLOAD"
