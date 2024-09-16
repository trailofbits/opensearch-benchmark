#!/bin/bash

ES_SNAPSHOT_S3_BUCKET=${s3_bucket_name}
WORKLOAD="big5"

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


# Restore the snapshot
curl -ku elastic:$ES_PASSWORD -X DELETE "$ES_HOST/$WORKLOAD?pretty"
curl -ku elastic:$ES_PASSWORD -X POST "$ES_HOST/_snapshot/$ES_SNAPSHOT_S3_BUCKET/snapshot_1/_restore" -H "Content-Type: application/json" -d"
{
  \"indices\": \"$WORKLOAD\"
}"
