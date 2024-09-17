#!/bin/bash

if [ -z "$CLUSTER_HOST" ] || [ -z "$CLUSTER_PASSWORD" ] || [ -z "$CLUSTER_VERSION" ]; then
    echo "Please set the CLUSTER_HOST, CLUSTER_PASSWORD and CLUSTER_VERSION environment variables"
    exit 1
fi

WORKLOAD="big5"
WORKLOAD_PARAMS=${workload_params}
CLIENT_OPTIONS="basic_auth_user:admin,basic_auth_password:$CLUSTER_PASSWORD,use_ssl:true,verify_certs:false"
TEST_EXECUTION_ID="os_$(date '+%Y_%m_%d_%H_%M_%S')"
RESULTS_FILE="/mnt/$TEST_EXECUTION_ID"

set -x

# Queries only
echo "Running Queries Only"
for i in $(seq 0 3)
do
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
                --distribution-version=$CLUSTER_VERSION
done

