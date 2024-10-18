#!/bin/bash

source /utils.sh

if [ $# -ne 2 ]; then
    echo "Usage: bash benchmark.sh <run-type> <run-id>"
    echo "  where <run-type> is 'official' or 'dev'"
    exit 1
fi

RUN_TYPE=$1
RUN_ID=$2

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

# Based on the workload, we can figure out the index name. It is mostly the same, but sometimes not.
INDEX_NAME=$(workload_index_name $WORKLOAD)

# This comes from the user `terraform.tfvars` configuration file
# shellcheck disable=SC2154
WORKLOAD_PARAMS="$${WORKLOAD_PARAMS:-${workload_params}}"

# This comes from the user `terraform.tfvars` configuration file
# shellcheck disable=SC2154
# When nothing is specified, the default test procedure is used.
TEST_PROCEDURE="$${TEST_PROCEDURE:-${test_procedure}}"

CLIENT_OPTIONS=$(join_by , "basic_auth_user:$CLUSTER_USER,basic_auth_password:$CLUSTER_PASSWORD,use_ssl:true,verify_certs:false" $EXTRA_CLIENT_OPTIONS)
RUN_GROUP_ID="$${RUN_GROUP_ID:-$(date '+%Y_%m_%d_%H_%M_%S')}"
AWS_LOADGEN_INSTANCE_ID="$(curl -m 5 -s http://169.254.169.254/latest/meta-data/instance-id)"

SHARD_COUNT="$(curl -m 5 -s --insecure --user "$CLUSTER_USER:$CLUSTER_PASSWORD" --request GET "$CLUSTER_HOST/$INDEX_NAME/_settings" | jq --raw-output ".\"$INDEX_NAME\".settings.index.number_of_shards")"
REPLICA_COUNT="$(curl -m 5 -s --insecure --user "$CLUSTER_USER:$CLUSTER_PASSWORD" --request GET "$CLUSTER_HOST/$INDEX_NAME/_settings" | jq --raw-output ".\"$INDEX_NAME\".settings.index.number_of_replicas")"

if [ -z "$SHARD_COUNT" ] || [ "$SHARD_COUNT" == "null" ]; then
    echo "Failed to retrieve the shard count"
    exit 1
fi

if [ -z "$REPLICA_COUNT" ] || [ "$REPLICA_COUNT" == "null" ]; then
    echo "Failed to retrieve the replica count"
    exit 1
fi

# assumes same machine for cluster
GROUP_USER_TAGS="run-group:$RUN_GROUP_ID,engine-type:$ENGINE_TYPE,arch:$(arch),instance-type:$INSTANCE_TYPE,aws-user-id:$AWS_USERID,aws-loadgen-instance-id:$AWS_LOADGEN_INSTANCE_ID"
GROUP_USER_TAGS+=",cluster-version:$CLUSTER_VERSION,workload-distribution-version:$DISTRIBUTION_VERSION,shard-count:$SHARD_COUNT,replica-count:$REPLICA_COUNT"
GROUP_USER_TAGS+=",run-type:$RUN_TYPE,aws-cluster-instance-id:$CLUSTER_INSTANCE_ID"
GROUP_USER_TAGS+=",cpu-model-name:$(lscpu | grep "Model name" | cut -d':' -f2 | xargs)"
GROUP_USER_TAGS+=",cpu-cache-l1d:$(lscpu | grep "L1d" | cut -d':' -f2 | xargs)"
GROUP_USER_TAGS+=",cpu-cache-l1i:$(lscpu | grep "L1i" | cut -d':' -f2 | xargs)"
GROUP_USER_TAGS+=",cpu-cache-l2:$(lscpu | grep "L2" | cut -d':' -f2 | xargs)"
GROUP_USER_TAGS+=",cpu-cache-l3:$(lscpu | grep "L3" | cut -d':' -f2 | xargs)"

set -x

EXECUTION_DIR="/mnt/test_executions"
mkdir -p "$EXECUTION_DIR"

# Queries only
echo "Running Queries Only"
check_params "$CLUSTER_USER" "$CLUSTER_PASSWORD" "$CLUSTER_HOST" "$WORKLOAD" "$INDEX_NAME"
TEST_EXECUTION_ID="cluster-$RUN_GROUP_ID-$RUN_ID"
RESULTS_FILE="$EXECUTION_DIR/$TEST_EXECUTION_ID"
USER_TAGS="$GROUP_USER_TAGS,run:$RUN_ID"
benchmark_single \
    "$WORKLOAD" \
    "$CLUSTER_HOST" \
    "$WORKLOAD_PARAMS" \
    "$CLIENT_OPTIONS" \
    "$RESULTS_FILE" \
    "$TEST_EXECUTION_ID" \
    "$TEST_PROCEDURE" \
    "$DISTRIBUTION_VERSION" \
    "$USER_TAGS"

check_params "$CLUSTER_USER" "$CLUSTER_PASSWORD" "$CLUSTER_HOST" "$WORKLOAD" "$INDEX_NAME"
