#!/bin/bash

source /utils.sh

# This comes from the user `terraform.tfvars` configuration file
# shellcheck disable=SC2154
SNAPSHOT_S3_BUCKET="${s3_bucket_name}"

# This comes from the user `terraform.tfvars` configuration file
# shellcheck disable=SC2154
WORKLOAD="$${WORKLOAD:-${workload}}"

# Based on the workload, we can figure out the index name. It is mostly the same, but somtimes not.
INDEX_NAME=$(workload_index_name $WORKLOAD)

# This comes from the user `terraform.tfvars` configuration file
# shellcheck disable=SC2154
WORKLOAD_PARAMS="$${WORKLOAD_PARAMS:-${workload_params}}"

SNAPSHOT_NAME=$(snapshot_name "$WORKLOAD" "$WORKLOAD_PARAMS")

# If SNAPSHOT_S3_BUCKET is not set, skip the snapshot
if [ -z "$SNAPSHOT_S3_BUCKET" ]; then
    echo "Skipping snapshot"
    exit 0
fi

# Register the S3 repository for snapshots
echo "Registering snapshot repository..."
register_snapshot_repo \
  "$CLUSTER_HOST" \
  "$CLUSTER_USER" \
  "$CLUSTER_PASSWORD" \
  "$SNAPSHOT_S3_BUCKET" \
  "$ENGINE_TYPE" \
  "$CLUSTER_VERSION" \
  "$WORKLOAD"

# Restore the snapshot
echo "Restoring snapshot..."
curl -ku $CLUSTER_USER:$CLUSTER_PASSWORD -X DELETE "$CLUSTER_HOST/$INDEX_NAME?pretty"
response=$(curl -ku $CLUSTER_USER:$CLUSTER_PASSWORD -X POST "$CLUSTER_HOST/_snapshot/$SNAPSHOT_S3_BUCKET/$SNAPSHOT_NAME/_restore?wait_for_completion=true" -H "Content-Type: application/json" -d"
{
  \"indices\": \"$INDEX_NAME\"
}")
echo "$response" | jq -e '.error' > /dev/null && {
  echo "Error in response from cluster"
  echo "$response"
  exit 3
}
echo "Snapshot restored"
