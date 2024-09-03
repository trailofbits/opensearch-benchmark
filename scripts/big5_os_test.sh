#!/bin/bash

set -e
source env/bin/activate
set -x

export JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64/

time opensearch-benchmark \
    execute-test \
    --pipeline=benchmark-only \
    --target-host="https://localhost:9200" \
    --client-options="basic_auth_user:admin,basic_auth_password:${OS_PASSWORD},verify_certs:false" \
    --workload=big5 \
    --workload-params corpus_size:60,number_of_replicas:0,target_throughput:"" \
    --results-file=/tmp/results \
    --kill-running-processes \
    --test-mode

curl -XGET "https://localhost:9200/_cat/indices?v" -u "admin:${OS_PASSWORD}" --insecure

echo "should only be 1000 documents for the index (usually) -- see index name in workload.json file"

set +ex
