#!/bin/bash

source /mnt/utils.sh

if [ -z "$CLUSTER_HOST" ] || [ -z "$CLUSTER_USER" ] || [ -z "$CLUSTER_PASSWORD" ] || [ -z "$DISTRIBUTION_VERSION" ]; then
    echo "Please set the CLUSTER_HOST, CLUSTER_USER, CLUSTER_PASSWORD and DISTRIBUTION_VERSION environment variables"
    exit 1
fi

# This comes from the user `terraform.tfvars` configuration file
# shellcheck disable=SC2154
SNAPSHOT_S3_BUCKET="${s3_bucket_name}"

# This comes from the user `terraform.tfvars` configuration file
# shellcheck disable=SC2154
SNAPSHOT_VERSION="${snapshot_version}"

# This comes from the user `terraform.tfvars` configuration file
# shellcheck disable=SC2154
WORKLOAD="$${WORKLOAD:-${workload}}"

# Based on the workload, we can figure out the index name. It is mostly the same, but somtimes not.
INDEX_NAME=$(workload_index_name $WORKLOAD)

# This comes from the user `terraform.tfvars` configuration file
# shellcheck disable=SC2154
WORKLOAD_PARAMS="$${WORKLOAD_PARAMS:-${workload_params}}"

CLIENT_OPTIONS=$(join_by , "basic_auth_user:$CLUSTER_USER,basic_auth_password:$CLUSTER_PASSWORD,use_ssl:true,verify_certs:false" $EXTRA_CLIENT_OPTIONS)
SNAPSHOT_NAME=$(snapshot_name "$WORKLOAD" "$WORKLOAD_PARAMS")

INGESTION_RESULTS=/mnt/ingestion_results
USER_TAGS="run-type:ingest,aws-user-id:$AWS_USERID,ci:$(ci_tag_value)"

# If the snapshot already exists, skip ingestion (check response.total > 0),
# unless FORCE_INGESTION is set
echo "Checking if snapshot already exists..."
register_snapshot_repo \
  "$CLUSTER_HOST" \
  "$CLUSTER_USER" \
  "$CLUSTER_PASSWORD" \
  "$SNAPSHOT_S3_BUCKET" \
  "$ENGINE_TYPE" \
  "$CLUSTER_VERSION" \
  "$WORKLOAD" \
  "$SNAPSHOT_VERSION"

response=$(curl -s -ku $CLUSTER_USER:$CLUSTER_PASSWORD -X GET "$CLUSTER_HOST/_snapshot/$SNAPSHOT_S3_BUCKET/$SNAPSHOT_NAME")
if [[ $(echo "$response" | jq -r '.snapshots | length') -gt 0 ]] && [ -z "$FORCE_INGESTION" ]; then
    echo "There's a snapshot already. Use /mnt/restore_snapshot.sh to restore it."
    echo "If you want to recreate the snapshot, set FORCE_INGESTION=true."
    exit 1
fi

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
    --distribution-version=$DISTRIBUTION_VERSION \
    --exclude-tasks="type:search" \
    --user-tag="$USER_TAGS" \
    --telemetry="node-stats"

check_params "$CLUSTER_USER" "$CLUSTER_PASSWORD" "$CLUSTER_HOST" "$WORKLOAD" "$INDEX_NAME"

# If SNAPSHOT_S3_BUCKET is not set, skip the snapshot
if [ -z "$SNAPSHOT_S3_BUCKET" ]; then
    echo "Skipping snapshot"
    exit 0
fi

# Delete the snapshot if it already exists
echo "Deleting snapshot..."
curl -s -ku $CLUSTER_USER:$CLUSTER_PASSWORD -X DELETE "$CLUSTER_HOST/_snapshot/$SNAPSHOT_S3_BUCKET/$SNAPSHOT_NAME"
echo "Snapshot deletion initiated, waiting for confirmation"
while true
do
  curl -s --max-time 5 -ku "$CLUSTER_USER:$CLUSTER_PASSWORD" "$CLUSTER_HOST"/_snapshot/$SNAPSHOT_S3_BUCKET/$SNAPSHOT_NAME | jq -e ".error" && break
  sleep 1
done
echo "Snapshot deleted"

# Perform the snapshot
echo "Performing snapshot..."
response=$(curl -ku $CLUSTER_USER:$CLUSTER_PASSWORD -X PUT "$CLUSTER_HOST/_snapshot/$SNAPSHOT_S3_BUCKET/$SNAPSHOT_NAME?wait_for_completion=true" -H "Content-Type: application/json" -d"
{
  \"indices\": \"$INDEX_NAME\"
}")
echo "$response" | jq -e '.error' > /dev/null && {
  echo "Error in response from Elasticsearch"
  echo "$response"
  exit 4
}
echo "Snapshot done"

bash /mnt/restore_snapshot.sh
