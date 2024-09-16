#!/bin/bash

if [ -z "$OS_HOST" ] || [ -z "$OS_PASSWORD" ] || [ -z "$OS_VERSION" ]; then
    echo "Please set the OS_HOST, OS_PASSWORD and OS_VERSION environment variables"
    exit 1
fi

WORKLOAD="big5"
WORKLOAD_PARAMS="number_of_replicas:0,bulk_indexing_clients:1,max_num_segments:10,target_throughput:0"
CLIENT_OPTIONS="basic_auth_user:admin,basic_auth_password:$OS_PASSWORD,use_ssl:true,verify_certs:false"
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
                --target-hosts="$OS_HOST" \
                --workload-params="$WORKLOAD_PARAMS" \
                --client-options="$CLIENT_OPTIONS" \
                --kill-running-processes \
                --include-tasks="type:search" \
                --results-file="$RESULTS_FILE-$i" \
                --test-execution-id="$TEST_EXECUTION_ID-$i" \
                --distribution-version=$OS_VERSION
done

