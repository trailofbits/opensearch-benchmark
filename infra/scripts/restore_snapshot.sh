#!/bin/bash

source /mnt/utils.sh

# This comes from the user `terraform.tfvars` configuration file
# shellcheck disable=SC2154
SNAPSHOT_S3_BUCKET="${s3_bucket_name}"

# This comes from the user `terraform.tfvars` configuration file
# shellcheck disable=SC2154
SNAPSHOT_VERSION="${snapshot_version}"

# This comes from the user `terraform.tfvars` configuration file
# shellcheck disable=SC2154
WORKLOAD="$${WORKLOAD:-${workload}}"
WORKLOAD_PARAMS=/mnt/workload_params.json

# Based on the workload, we can figure out the index name. It is mostly the same, but somtimes not.
INDEX_NAME=$(workload_index_name $WORKLOAD)

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
  "$WORKLOAD" \
  "$SNAPSHOT_VERSION"

# Restore the snapshot
echo "Restoring snapshot..."

# Keep trying to restore the snapshot until it's successful
retries=10
while true; do
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

  # Check if the snapshot was restored successfully
  if [[ $(echo "$response" | jq -r '.snapshot.shards.failed') == "0" ]]; then
      break
  fi
  if [ $retries -eq 0 ]; then
      echo "Snapshot restore failed"
      exit 1
  fi

  echo "Snapshot restore failed. Retrying in 5 seconds..."
  sleep 8
  retries=$((retries - 1))
done

# Lets complete a refresh
echo "Doing a Flush to commit all the segments"
curl -s -ku $CLUSTER_USER:$CLUSTER_PASSWORD -X POST "$CLUSTER_HOST/$INDEX_NAME/_flush"

echo "Doing a Refresh after flush"
curl -s -ku $CLUSTER_USER:$CLUSTER_PASSWORD -X POST "$CLUSTER_HOST/$INDEX_NAME/_refresh"

echo "Sleeping for 30 sec before we can fetch the merge stats"
sleep 30
echo "Getting merge stats"
while true
do
  # gather all the merge stats
  merge_stats=$(curl -s -ku $CLUSTER_USER:$CLUSTER_PASSWORD -X GET "$CLUSTER_HOST/_nodes/stats?filter_path=nodes.*.indices.merges&format=json")
  # Find the current state of the merges
  current_merges=$(echo "$merge_stats" | jq -r '.nodes | to_entries[] | .value.indices.merges | .current')

  all_merges_completed=1
  for i in $current_merges; do
    echo "Current merges: $i"
    if [ "$i" -gt 0 ]; then
      echo "Merges are still in progress, waiting for them to finish. Sleeping for 30 sec"
      all_merges_completed=0
      break
    fi
  done

  if [ $all_merges_completed -eq 1 ]; then
    echo "All merges are completed. Exiting from the loop"
    break
  fi
  echo "Merges are still in progress, waiting for them to finish. Sleeping for 30 sec"
  sleep 30
done

echo "Doing a final refresh before using the snapshot"
curl -s -ku $CLUSTER_USER:$CLUSTER_PASSWORD -X POST "$CLUSTER_HOST/$INDEX_NAME/_refresh"

echo "Snapshot restored"
check_params "$CLUSTER_USER" "$CLUSTER_PASSWORD" "$CLUSTER_HOST" "$WORKLOAD" "$INDEX_NAME"
