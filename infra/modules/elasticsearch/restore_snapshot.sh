#!/bin/bash

ES_SNAPSHOT_S3_BUCKET=${s3_bucket_name}
WORKLOAD="big5"

# If ES_SNAPSHOT_S3_BUCKET is not set, skip the snapshot
if [ -z "$ES_SNAPSHOT_S3_BUCKET" ]; then
    echo "Skipping snapshot"
    exit 0
fi

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
  \"indices\": \"$WORKLOAD\"
}"
