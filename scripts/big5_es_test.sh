#!/bin/bash

set -e
source env/bin/activate
set -x

export JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64/

#   --workload-params corpus_size:60,number_of_replicas:0,target_throughput:"" \
#   --workload-params number_of_replicas:0,bulk_indexing_clients:1,force_merge_max_num_segments:t,max_num_segments:10 \

time opensearch-benchmark \
    execute-test \
    --distribution-version=8.0.0 \
    --pipeline=benchmark-only \
    --target-hosts="https://localhost:9200" \
    --client-options="basic_auth_user:elastic,basic_auth_password:${ES_PASSWORD},use_ssl:true,verify_certs:false" \
    --workload=big5 \
    --workload-params "number_of_replicas:0,bulk_indexing_clients:1,max_num_segments:10" \
    --kill-running-processes \
    --test-mode

curl -XGET "https://localhost:9200/_cat/indices?v" -u "elastic:${ES_PASSWORD}" --insecure

echo "should only be 1000 documents for the index (usually) -- see index name in workload.json file"

set +ex
