#!/bin/bash

# Check if CLUSTER_HOST, and CLUSTER_PASSWORD env vars are set
if [ -z "$CLUSTER_HOST" ] || [ -z "$CLUSTER_PASSWORD" ]; then
    echo "Please set the CLUSTER_HOST, and CLUSTER_PASSWORD environment variables"
    exit 1
fi

WORKLOAD="big5"
WORKLOAD_PARAMS="${workload_params}"
CLIENT_OPTIONS="basic_auth_user:elastic,basic_auth_password:$CLUSTER_PASSWORD,use_ssl:true,verify_certs:false"
TEST_EXECUTION_ID="es-query-benchmark"
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
                --distribution-version=8.15.0
done

