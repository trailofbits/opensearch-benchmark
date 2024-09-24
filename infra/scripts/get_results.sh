#!/bin/bash
set -e
if [ $# -ne 1 ]; then
    echo "Usage: bash get_results.sh <output-folder>"
    exit 1
fi
OUTPUT_DIR=$1
REMOTE_PATH="/mnt/test_executions/*"
rsync --ignore-existing "ubuntu@$(terraform output -raw load-generation-ip):$REMOTE_PATH" "$OUTPUT_DIR"
