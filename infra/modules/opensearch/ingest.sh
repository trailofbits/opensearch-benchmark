#!/bin/bash

if [ -z "$OS_HOST" ] || [ -z "$OS_PASSWORD" ] || [ -z "$OS_VERSION" ]; then
    echo "Please set the OS_HOST, OS_PASSWORD and OS_VERSION environment variables"
    exit 1
fi

WORKLOAD="big5"
WORKLOAD_PARAMS=${workload_params}
CLIENT_OPTIONS="basic_auth_user:admin,basic_auth_password:$OS_PASSWORD,use_ssl:true,verify_certs:false"

INGESTION_RESULTS=/mnt/ingestion_results

# Ingest data in the OS cluster
opensearch-benchmark execute-test \
    --pipeline=benchmark-only \
    --workload=$WORKLOAD \
    --target-hosts="$OS_HOST" \
    --workload-params="$WORKLOAD_PARAMS" \
    --client-options="$CLIENT_OPTIONS" \
    --kill-running-processes \
    --results-file=$INGESTION_RESULTS \
    --test-execution-id=ingestion \
    --distribution-version=$OS_VERSION \
    --exclude-tasks="type:search"
