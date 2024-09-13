#!/bin/bash

# Check if ES_HOST, and ES_PASSWORD env vars are set
if [ -z "$ES_HOST" ] || [ -z "$ES_PASSWORD" ]; then
    echo "Please set the ES_HOST, and ES_PASSWORD environment variables"
    exit 1
fi

ES_SNAPSHOT_S3_BUCKET=${s3_bucket_name}
WORKLOAD="big5"
WORKLOAD_PARAMS="number_of_replicas:0,bulk_indexing_clients:1,max_num_segments:10,target_throughput:0"
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

# Register the S3 repository for snapshots
curl -s -ku elastic:$ES_PASSWORD -X PUT "$ES_HOST/_snapshot/$ES_SNAPSHOT_S3_BUCKET?pretty" -H 'Content-Type: application/json' -d"
{
  \"type\": \"s3\",
  \"settings\": {
    \"bucket\": \"$ES_SNAPSHOT_S3_BUCKET\"
  }
}
" || exit 3

# Perform the snapshot
curl -ku elastic:$ES_PASSWORD -X PUT "$ES_HOST/_snapshot/$ES_SNAPSHOT_S3_BUCKET/snapshot_1" -H "Content-Type: application/json" -d"
{
  \"indices\": \"$WORKLOAD\",
  \"ignore_unavailable\": true,
  \"include_global_state\": false
}" || exit 4

# Wait until the snapshot is in SUCCESS state
while true; do
  STATUS=$(curl -s -ku elastic:$ES_PASSWORD -X GET "$ES_HOST/_snapshot/$ES_SNAPSHOT_S3_BUCKET/snapshot_1/_status?pretty" | jq -r '.snapshots[0].state')
  if [ "$STATUS" == "SUCCESS" ]; then
    break
  fi
  echo "Snapshot status: $STATUS, waiting for it to be SUCCESS"
  sleep 5
done

# Restore the snapshot
curl -ku elastic:$ES_PASSWORD -X DELETE "$ES_HOST/$WORKLOAD?pretty"
curl -ku elastic:$ES_PASSWORD -X POST "$ES_HOST/_snapshot/$ES_SNAPSHOT_S3_BUCKET/snapshot_1/_restore" -H "Content-Type: application/json" -d"
{
  \"indices\": \"$WORKLOAD\",
}"
