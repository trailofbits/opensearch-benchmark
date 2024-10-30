#!/bin/bash

ES_TF_WORKSPACE=$1
OS_TF_WORKSPACE=$2
QUERY_FILE=$3

run_ssh_cmd() {
    local cmd=$1
    ssh -i "$(terraform output -raw ssh_private_key_file)" -t "ubuntu@$(terraform output -raw load-generation-ip)" -- "bash -ic \"$cmd\""
}

cp_scp() {
    local src=$1
    local dest=$2
    scp -i "$(terraform output -raw ssh_private_key_file)" "$src" "ubuntu@$(terraform output -raw load-generation-ip):$dest"
}

# Move to ES terraform workspace and run query
terraform workspace select "$ES_TF_WORKSPACE"
cp_scp "$QUERY_FILE" "query.json"
ES_RESULTS=$(run_ssh_cmd "curl -s -ku \\\$CLUSTER_USER:\\\$CLUSTER_PASSWORD \\\$CLUSTER_HOST/big5/_search -H 'Content-Type: application/json' -d @query.json")
ES_EXPLAIN_RESULTS=$(run_ssh_cmd "curl -s -ku \\\$CLUSTER_USER:\\\$CLUSTER_PASSWORD \\\$CLUSTER_HOST/big5/_validate/query?pretty\&explain=true -H 'Content-Type: application/json' -d @query.json")

# Move to OS terraform workspace and run query
terraform workspace select "$OS_TF_WORKSPACE"
cp_scp "$QUERY_FILE" "query.json"
OS_RESULTS=$(run_ssh_cmd "curl -s -ku \\\$CLUSTER_USER:\\\$CLUSTER_PASSWORD \\\$CLUSTER_HOST/big5/_search -H 'Content-Type: application/json' -d @query.json")
OS_EXPLAIN_RESULTS=$(run_ssh_cmd "curl -s -ku \\\$CLUSTER_USER:\\\$CLUSTER_PASSWORD \\\$CLUSTER_HOST/big5/_validate/query?pretty\&explain=true -H 'Content-Type: application/json' -d @query.json")

echo "$ES_RESULTS" | jq > es-results.json
echo "$OS_RESULTS" | jq > os-results.json

echo "$ES_EXPLAIN_RESULTS" > es-explain-results.json
echo "$OS_EXPLAIN_RESULTS" > os-explain-results.json
