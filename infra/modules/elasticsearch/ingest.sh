#!/bin/bash

# Check if ES_HOST, and ES_PASSWORD env vars are set
if [ -z "$ES_HOST" ] || [ -z "$ES_PASSWORD" ]; then
    echo "Please set the ES_HOST, and ES_PASSWORD environment variables"
    exit 1
fi

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
ES_SNAPSHOT_S3_BUCKET=${s3_bucket_name}
WORKLOAD="big5"
WORKLOAD_PARAMS="${workload_params}"
CLIENT_OPTIONS="basic_auth_user:elastic,basic_auth_password:$ES_PASSWORD,use_ssl:true,verify_certs:false"

INGESTION_RESULTS=/mnt/ingestion_results

# Ingest data in the ES cluster
opensearch-benchmark execute-test \
    --pipeline=benchmark-only \
    --workload=$WORKLOAD \
    --target-hosts="$ES_HOST" \
    --workload-params="$WORKLOAD_PARAMS" \
    --client-options="$CLIENT_OPTIONS" \
    --kill-running-processes \
    --results-file=$INGESTION_RESULTS \
    --test-execution-id=ingestion \
    --distribution-version=8.15.0 \
    --exclude-tasks="type:search" || exit 2

# If ES_SNAPSHOT_S3_BUCKET is not set, skip the snapshot
if [ -z "$ES_SNAPSHOT_S3_BUCKET" ]; then
    echo "Skipping snapshot"
    exit 0
fi

# Register the S3 repository for snapshots
response=$(curl -s -ku elastic:$ES_PASSWORD -X PUT "$ES_HOST/_snapshot/$ES_SNAPSHOT_S3_BUCKET?pretty" -H 'Content-Type: application/json' -d"
{
  \"type\": \"s3\",
  \"settings\": {
    \"bucket\": \"$ES_SNAPSHOT_S3_BUCKET\"
  }
}
")
echo "$response" | jq -e '.error' > /dev/null && {
  echo "Error in response from Elasticsearch"
  echo "$response"
  exit 3
}

# Perform the snapshot
response=$(curl -ku elastic:$ES_PASSWORD -X PUT "$ES_HOST/_snapshot/$ES_SNAPSHOT_S3_BUCKET/snapshot_1" -H "Content-Type: application/json" -d"
{
  \"indices\": \"$WORKLOAD\"
}")
echo "$response" | jq -e '.error' > /dev/null && {
  echo "Error in response from Elasticsearch"
  echo "$response"
  exit 4
}

$SCRIPT_DIR/restore_snapshot.sh
