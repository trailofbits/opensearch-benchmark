#!/bin/bash

source /utils.sh

if [ -z "$CLUSTER_HOST" ] || [ -z "$CLUSTER_USER" ] || [ -z "$CLUSTER_PASSWORD" ] || [ -z "$DISTRIBUTION_VERSION" ]; then
    echo "Please set the CLUSTER_HOST, CLUSTER_USER, CLUSTER_PASSWORD and DISTRIBUTION_VERSION environment variables"
    exit 1
fi

# This comes from the user `terraform.tfvars` configuration file
# shellcheck disable=SC2154
WORKLOAD="$${WORKLOAD:-${workload}}"

# This comes from the user `terraform.tfvars` configuration file
# shellcheck disable=SC2154
WORKLOAD_PARAMS="$${WORKLOAD_PARAMS:-${workload_params}}"

CLIENT_OPTIONS="basic_auth_user:$CLUSTER_USER,basic_auth_password:$CLUSTER_PASSWORD,use_ssl:true,verify_certs:false"
TEST_EXECUTION_ID="cluster_$(date '+%Y_%m_%d_%H_%M_%S')"
RESULTS_FILE="/mnt/$TEST_EXECUTION_ID"

set -x

# Queries only
echo "Running Queries Only"
for i in $(seq 0 4)
do
        check_params "$CLUSTER_USER" "$CLUSTER_PASSWORD" "$CLUSTER_HOST" "$WORKLOAD"
        opensearch-benchmark execute-test \
                --pipeline=benchmark-only \
                --workload=$WORKLOAD  \
                --target-hosts="$CLUSTER_HOST" \
                --workload-params="$WORKLOAD_PARAMS" \
                --client-options="$CLIENT_OPTIONS" \
                --kill-running-processes \
                --include-tasks="type:search" \
                --results-file="$RESULTS_FILE-$i" \
                --test-execution-id="$TEST_EXECUTION_ID-$i" \
                --distribution-version=$DISTRIBUTION_VERSION \
                --user-tag "run:$i"
done

check_params "$CLUSTER_USER" "$CLUSTER_PASSWORD" "$CLUSTER_HOST" "$WORKLOAD"
