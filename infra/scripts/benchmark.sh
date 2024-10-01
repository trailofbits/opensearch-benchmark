#!/bin/bash

source /utils.sh

if [ $# -ne 1 ]; then
    echo "Usage: bash benchmark.sh <run-type>"
    echo "  where <run-type> is 'official' or 'dev'"
    exit 1
fi

RUN_TYPE=$1

if [ "$RUN_TYPE" != "official" ] && [ "$RUN_TYPE" != "dev" ]; then
    echo "Error: <run-type> must be 'official' or 'dev'"
    exit 1
fi

if [ -z "$CLUSTER_HOST" ] || [ -z "$CLUSTER_USER" ] || [ -z "$CLUSTER_PASSWORD" ] || [ -z "$DISTRIBUTION_VERSION" ] || [ -z "$CLUSTER_VERSION" ] || [ -z "$ENGINE_TYPE" ] || [ -z "$INSTANCE_TYPE" ]; then
    echo "Please set the CLUSTER_HOST, CLUSTER_USER, CLUSTER_PASSWORD, DISTRIBUTION_VERSION, CLUSTER_VERSION, ENGINE_TYPE, and INSTANCE_TYPE environment variables"
    exit 1
fi

# This comes from the user `terraform.tfvars` configuration file
# shellcheck disable=SC2154
WORKLOAD="$${WORKLOAD:-${workload}}"

# Based on the workload, we can figure out the index name. It is mostly the same, but somtimes not.
INDEX_NAME=$(workload_index_name $WORKLOAD)

# This comes from the user `terraform.tfvars` configuration file
# shellcheck disable=SC2154
WORKLOAD_PARAMS="$${WORKLOAD_PARAMS:-${workload_params}}"

CLIENT_OPTIONS="basic_auth_user:$CLUSTER_USER,basic_auth_password:$CLUSTER_PASSWORD,use_ssl:true,verify_certs:false"
RUN_GROUP_ID="$(date '+%Y_%m_%d_%H_%M_%S')"
AWS_ACCOUNT_ID="$(curl -m 5 -s http://169.254.169.254/latest/dynamic/instance-identity/document | jq -r .accountId)"
AWS_LOADGEN_INSTANCE_ID="$(curl -m 5 -s http://169.254.169.254/latest/meta-data/instance-id)"
SHARD_COUNT="$(curl -m 5 -s --insecure --user "$CLUSTER_USER:$CLUSTER_PASSWORD" --request GET "$CLUSTER_HOST/$WORKLOAD/_settings" | jq --raw-output ".$WORKLOAD.settings.index.number_of_shards")"
REPLICA_COUNT="$(curl -m 5 -s --insecure --user "$CLUSTER_USER:$CLUSTER_PASSWORD" --request GET "$CLUSTER_HOST/$WORKLOAD/_settings" | jq --raw-output ".$WORKLOAD.settings.index.number_of_replicas")"
# assumes same machine for cluster
GROUP_USER_TAGS="run-group:$RUN_GROUP_ID,engine-type:$ENGINE_TYPE,arch:$(arch),instance-type:$INSTANCE_TYPE,aws-account-id:$AWS_ACCOUNT_ID,aws-loadgen-instance-id:$AWS_LOADGEN_INSTANCE_ID"
GROUP_USER_TAGS+=",cluster-version:$CLUSTER_VERSION,workload-distribution-version:$DISTRIBUTION_VERSION,shard-count:$SHARD_COUNT,replica-count:$REPLICA_COUNT"

set -x

EXECUTION_DIR="/mnt/test_executions"
mkdir -p "$EXECUTION_DIR"

# Queries only
echo "Running Queries Only"
for i in $(seq 0 4)
do
        check_params "$CLUSTER_USER" "$CLUSTER_PASSWORD" "$CLUSTER_HOST" "$WORKLOAD" "$INDEX_NAME"
        TEST_EXECUTION_ID="cluster-$RUN_GROUP_ID-$i"
        RESULTS_FILE="$EXECUTION_DIR/$TEST_EXECUTION_ID"
        USER_TAGS="$GROUP_USER_TAGS,run:$i"
        # tag first run as a warmup
        if [[ $i -eq 0 ]]; then
            USER_TAGS+=",run-type:warmup"
        else
            USER_TAGS+=",run-type:$RUN_TYPE"
        fi
        opensearch-benchmark execute-test \
                --pipeline=benchmark-only \
                --workload=$WORKLOAD  \
                --target-hosts="$CLUSTER_HOST" \
                --workload-params="$WORKLOAD_PARAMS" \
                --client-options="$CLIENT_OPTIONS" \
                --kill-running-processes \
                --include-tasks="type:search" \
                --results-file="$RESULTS_FILE" \
                --test-execution-id="$TEST_EXECUTION_ID" \
                --distribution-version=$DISTRIBUTION_VERSION \
                --user-tag="$USER_TAGS" \
                --telemetry="node-stats"
done

check_params "$CLUSTER_USER" "$CLUSTER_PASSWORD" "$CLUSTER_HOST" "$WORKLOAD" "$INDEX_NAME"
