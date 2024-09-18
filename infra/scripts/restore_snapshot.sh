#!/bin/bash

SNAPSHOT_S3_BUCKET=${s3_bucket_name}
WORKLOAD="big5"
WORKLOAD_PARAMS="${workload_params}"
SNAPSHOT_NAME=$(echo "$WORKLOAD;$WORKLOAD_PARAMS" | md5sum | cut -d' ' -f1)

# If SNAPSHOT_S3_BUCKET is not set, skip the snapshot
if [ -z "$SNAPSHOT_S3_BUCKET" ]; then
    echo "Skipping snapshot"
    exit 0
fi

# Register the S3 repository for snapshots
response=$(curl -s -ku $CLUSTER_USER:$CLUSTER_PASSWORD -X PUT "$CLUSTER_HOST/_snapshot/$SNAPSHOT_S3_BUCKET?pretty" -H 'Content-Type: application/json' -d"
{
  \"type\": \"s3\",
  \"settings\": {
    \"bucket\": \"$SNAPSHOT_S3_BUCKET\"
  }
}
")
echo "$response" | jq -e '.error' > /dev/null && {
  echo "Error in response from cluster"
  echo "$response"
  exit 3
}


# Restore the snapshot
curl -ku $CLUSTER_USER:$CLUSTER_PASSWORD -X DELETE "$CLUSTER_HOST/$WORKLOAD?pretty"
curl -ku $CLUSTER_USER:$CLUSTER_PASSWORD -X POST "$CLUSTER_HOST/_snapshot/$SNAPSHOT_S3_BUCKET/$SNAPSHOT_NAME/_restore" -H "Content-Type: application/json" -d"
{
  \"indices\": \"$WORKLOAD\"
}"


# Wait until the restore is complete (stage == "DONE")
while [ "$(curl -s -ku $CLUSTER_USER:$CLUSTER_PASSWORD "$CLUSTER_HOST/_recovery" | jq -r ".[\"$WORKLOAD\"][\"shards\"] | .[].stage" | sort | uniq)" != "DONE" ]; do
  echo "Waiting for restore to complete"
  sleep 10
done
