#!/bin/bash
set -e
# Download results for a test run group from metric data store (INCLUDING WARMUP)
# Similar functionality to get_results.sh, except for using the data store
# Usage: bash get_datastore_results.sh output-folder run_group_id
# Example: bash get_datastore_results.sh result-dir 2024_09_20_13_56_42
# DS_HOSTNAME: data store hostname
# DS_USERNAME: data store username
# DS_PASSWORD: data store password

# Check if all required parameters are provided
if [ "$#" -ne 2 ]; then
    echo "Usage: $0 <output-folder> <run_group_id>"
    exit 1
fi

if [[ -z "$DS_HOSTNAME" || -z "$DS_USERNAME" || -z "$DS_PASSWORD" ]]; then
    echo "Must set environment variables: DS_HOSTNAME, DS_USERNAME, DS_PASSWORD"
    exit 1
fi

OUTPUT_DIR=$1
RUN_GROUP_ID=$2

QUERY_OUTPUT="$(mktemp)"
mkdir "$OUTPUT_DIR"

# Download results from data store
curl -X GET "https://${DS_HOSTNAME}/benchmark-test-*/_search" \
-u "${DS_USERNAME}:${DS_PASSWORD}" \
-H "Content-Type: application/json" \
-d "{
    \"size\": 100,
    \"query\": {
        \"bool\": {
            \"must\": [
                {
                    \"term\": {
                        \"user-tags.run-group\": \"${RUN_GROUP_ID}\"
                    }
                }
            ]
        }
    }
}" \
--insecure > "$QUERY_OUTPUT" \
2> /dev/null

HITS=$(jq '.hits.hits | length' "$QUERY_OUTPUT")

for i in $(seq 0 $(($HITS-1))); do
    jq ".hits.hits.[] | select(._source.\"user-tags\".run == \"$i\") | ._source" "$QUERY_OUTPUT" > "$OUTPUT_DIR/res-$i.json"
done

rm "$QUERY_OUTPUT"
