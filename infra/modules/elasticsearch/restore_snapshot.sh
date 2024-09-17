#!/bin/bash

ES_SNAPSHOT_S3_BUCKET=${s3_bucket_name}
WORKLOAD="big5"
WORKLOAD_PARAMS="${workload_params}"
SNAPSHOT_NAME=$(echo "$WORKLOAD;$WORKLOAD_PARAMS" | md5sum | cut -d' ' -f1)

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


# Restore the snapshot
curl -ku elastic:$CLUSTER_PASSWORD -X DELETE "$CLUSTER_HOST/$WORKLOAD?pretty"
curl -ku elastic:$CLUSTER_PASSWORD -X POST "$CLUSTER_HOST/_snapshot/$ES_SNAPSHOT_S3_BUCKET/$SNAPSHOT_NAME/_restore" -H "Content-Type: application/json" -d"
{
  \"indices\": \"$WORKLOAD\"
}"
