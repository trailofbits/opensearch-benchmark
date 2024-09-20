#!/bin/bash
set -e
# Download results for a test run from metric data store and print summary
# Usage: bash get_datastore_results.sh benchmark_results_index test_execution_id
# Example: bash get_datastore_results.sh benchmark-results-2024-09 cluster_2024_09_20_13_56_42-3
# DS_HOSTNAME: data store hostname
# DS_USERNAME: data store username
# DS_PASSWORD: data store password

# Check if all required parameters are provided
if [ "$#" -ne 2 ]; then
    echo "Usage: $0 <index_name> <test_exec_id>"
    exit 1
fi

if [[ -z "$DS_HOSTNAME" || -z "$DS_USERNAME" || -z "$DS_PASSWORD" ]]; then
    echo "Must set environment variables: DS_HOSTNAME, DS_USERNAME, DS_PASSWORD"
    exit 1
fi

INDEX_NAME=$1
EXEC_ID=$2

OUTPUT_JSON="res-${EXEC_ID}.json"

# Download results from data store
curl -X GET "https://${DS_HOSTNAME}/${INDEX_NAME}/_search" \
-u "${DS_USERNAME}:${DS_PASSWORD}" \
-H "Content-Type: application/json" \
-d "{
  \"size\": 1000,
  \"query\": {
    \"term\": {
      \"test-execution-id\": \"${EXEC_ID}\"
    }
  }
}" \
--insecure > "$OUTPUT_JSON" \
2> /dev/null

echo "Got results for the tasks:"
jq '.hits.hits[] | ._source.task' "$OUTPUT_JSON" | sort -u | tr -d '"' | grep -v '^null$'
