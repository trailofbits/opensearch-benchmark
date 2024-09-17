#!/bin/bash

OUTPUT_DIR=$1
RESULT_COUNT=4
REMOTE_PATH="/mnt/test_executions"
latest_result_ids=$(ssh ubuntu@$(terraform output -raw load-generation-ip) "ls -t ${REMOTE_PATH} | head -n ${RESULT_COUNT}")
echo "$latest_result_ids" | while read -r result_id; do
    scp ubuntu@$(terraform output -raw load-generation-ip):$REMOTE_PATH/$result_id/test_execution.json $OUTPUT_DIR/res-$result_id.json
done
