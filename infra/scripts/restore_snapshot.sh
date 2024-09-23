#!/bin/bash

SNAPSHOT_S3_BUCKET=${s3_bucket_name}
WORKLOAD="${workload}"
WORKLOAD_PARAMS="${workload_params}"
SNAPSHOT_NAME=$(echo "$WORKLOAD;$WORKLOAD_PARAMS" | md5sum | cut -d' ' -f1)

# If SNAPSHOT_S3_BUCKET is not set, skip the snapshot
if [ -z "$SNAPSHOT_S3_BUCKET" ]; then
    echo "Skipping snapshot"
    exit 0
fi

# Register the S3 repository for snapshots
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
  echo "Error in response from cluster"
  echo "$response"
  exit 3
}


# Restore the snapshot
echo "Restoring snapshot..."
curl -ku $CLUSTER_USER:$CLUSTER_PASSWORD -X DELETE "$CLUSTER_HOST/$WORKLOAD?pretty"
curl -ku $CLUSTER_USER:$CLUSTER_PASSWORD -X POST "$CLUSTER_HOST/_snapshot/$SNAPSHOT_S3_BUCKET/$SNAPSHOT_NAME/_restore?wait_for_completion=true" -H "Content-Type: application/json" -d"
{
  \"indices\": \"$WORKLOAD\"
}"
echo "Snapshot restored"
