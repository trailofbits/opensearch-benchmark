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

if [ -z "$CLUSTER_HOST" ] || [ -z "$CLUSTER_USER" ] || [ -z "$CLUSTER_PASSWORD" ] || [ -z "$CLUSTER_VERSION" ] || [ -z "$ENGINE_TYPE" ] || [ -z "$INSTANCE_TYPE" ]; then
    echo "Please set the CLUSTER_HOST, CLUSTER_USER, CLUSTER_PASSWORD, CLUSTER_VERSION, ENGINE_TYPE, and INSTANCE_TYPE environment variables"
    exit 1
fi

# This comes from the user `terraform.tfvars` configuration file
# shellcheck disable=SC2154
WORKLOAD="${workload}"

# This comes from the user `terraform.tfvars` configuration file
# shellcheck disable=SC2154
WORKLOAD_PARAMS="${workload_params}"

CLIENT_OPTIONS="basic_auth_user:$CLUSTER_USER,basic_auth_password:$CLUSTER_PASSWORD,use_ssl:true,verify_certs:false"
RUN_GROUP_ID="$(date '+%Y_%m_%d_%H_%M_%S')"
# assumes same machine for cluster
GROUP_USER_TAGS="run-group:$RUN_GROUP_ID,engine-type:$ENGINE_TYPE,arch:$(arch),instance-type:$INSTANCE_TYPE,run-type:$RUN_TYPE"

set -x

# Queries only
echo "Running Queries Only"
for i in $(seq 0 3)
do
        check_params "$CLUSTER_USER" "$CLUSTER_PASSWORD" "$CLUSTER_HOST" "$WORKLOAD"
        TEST_EXECUTION_ID="cluster-$RUN_GROUP_ID-$i"
        RESULTS_FILE="/mnt/$TEST_EXECUTION_ID"
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
                --distribution-version=$CLUSTER_VERSION \
                --user-tag="$GROUP_USER_TAGS" \
                --telemetry="node-stats"
done

check_params "$CLUSTER_USER" "$CLUSTER_PASSWORD" "$CLUSTER_HOST" "$WORKLOAD"
