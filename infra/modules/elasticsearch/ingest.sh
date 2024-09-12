#!/bin/bash

# Check if ES_HOST, and ES_PASSWORD env vars are set
if [ -z "$ES_HOST" ] || [ -z "$ES_PASSWORD" ]; then
    echo "Please set the ES_HOST, and ES_PASSWORD environment variables"
    exit 1
fi

WORKLOAD="big5"
WORKLOAD_PARAMS="number_of_replicas:0,bulk_indexing_clients:1,max_num_segments:10,target_throughput:0"
CLIENT_OPTIONS="basic_auth_user:elastic,basic_auth_password:$ES_PASSWORD,use_ssl:true,verify_certs:false"

INGESTION_RESULTS=/mnt/ingestion_results

# Ingest data in the ES cluster
opensearch-benchmark execute-test \
    --pipeline=benchmark-only \
    --workload=$WORKLOAD \
    --target-hosts="$ES_HOST" \
    --workload-params="$WORKLOAD_PARAMS" \
    --client-options="$CLIENT_OPTIONS" \
    --kill-running-processes \
    --results-file=$INGESTION_RESULTS \
    --test-execution-id=ingestion \
    --distribution-version=8.15.0 \
    --exclude-tasks="type:search"
