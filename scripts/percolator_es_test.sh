#!/bin/bash

set -e
source env/bin/activate
set -x

export JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64/

time opensearch-benchmark \
    execute-test \
    --pipeline=benchmark-only \
    --target-host="https://localhost:9200" \
    --client-options="basic_auth_user:elastic,basic_auth_password:${ES_PASSWORD}",verify_certs:false \
    --workload=percolator \
    --test-mode \
    --kill-running-processes

curl -XGET "https://localhost:9200/_cat/indices?v" -u "elastic:${ES_PASSWORD}" --insecure

echo "should only be 1000 documents for the index (usually) -- see index name in workload.json file"

set +ex
