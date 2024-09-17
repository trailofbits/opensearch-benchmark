#!/bin/bash

if [ -z "$CLUSTER_HOST" ] || [ -z "$CLUSTER_USER" ] || [ -z "$CLUSTER_PASSWORD" ] || [ -z "$CLUSTER_VERSION" ]; then
    echo "Please set the CLUSTER_HOST, CLUSTER_USER, CLUSTER_PASSWORD and CLUSTER_VERSION environment variables"
    exit 1
fi

ES_SNAPSHOT_S3_BUCKET=${s3_bucket_name}
WORKLOAD="big5"
WORKLOAD_PARAMS=${workload_params}
CLIENT_OPTIONS="basic_auth_user:$CLUSTER_USER,basic_auth_password:$CLUSTER_PASSWORD,use_ssl:true,verify_certs:false"
SNAPSHOT_NAME=$(echo "$WORKLOAD;$WORKLOAD_PARAMS" | md5sum | cut -d' ' -f1)

INGESTION_RESULTS=/mnt/ingestion_results

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

# If ES_SNAPSHOT_S3_BUCKET is not set, skip the snapshot
if [ -z "$ES_SNAPSHOT_S3_BUCKET" ]; then
    echo "Skipping snapshot"
    exit 0
fi

# Register the S3 repository for snapshots
response=$(curl -s -ku elastic:$CLUSTER_PASSWORD -X PUT "$CLUSTER_HOST/_snapshot/$ES_SNAPSHOT_S3_BUCKET?pretty" -H 'Content-Type: application/json' -d"
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
response=$(curl -ku elastic:$CLUSTER_PASSWORD -X PUT "$CLUSTER_HOST/_snapshot/$ES_SNAPSHOT_S3_BUCKET/$SNAPSHOT_NAME" -H "Content-Type: application/json" -d"
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
  STATUS=$(curl -s -ku elastic:$CLUSTER_PASSWORD -X GET "$CLUSTER_HOST/_snapshot/$ES_SNAPSHOT_S3_BUCKET/$SNAPSHOT_NAME/_status?pretty" | jq -r '.snapshots[0].state')
  if [ "$STATUS" == "SUCCESS" ]; then
    break
  fi
  echo "Snapshot status: $STATUS, waiting for it to be SUCCESS"
  sleep 5
done

# Restore the snapshot
curl -ku elastic:$CLUSTER_PASSWORD -X DELETE "$CLUSTER_HOST/$WORKLOAD?pretty"
curl -ku elastic:$CLUSTER_PASSWORD -X POST "$CLUSTER_HOST/_snapshot/$ES_SNAPSHOT_S3_BUCKET/$SNAPSHOT_NAME/_restore" -H "Content-Type: application/json" -d"
{
  \"indices\": \"$WORKLOAD\"
}"
