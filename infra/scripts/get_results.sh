#!/bin/bash
set -e
if [ $# -ne 1 ]; then
    echo "Usage: bash get_results.sh <output-folder>"
    exit 1
fi
OUTPUT_DIR=$1

mkdir -p "$OUTPUT_DIR"

REMOTE_PATH="/mnt/.benchmark/benchmarks/test_executions/cluster*"
TMP_DIR="$(mktemp -d)"
rsync -r --ignore-existing "ubuntu@$(terraform output -raw load-generation-ip):$REMOTE_PATH" "$TMP_DIR"

# Move all files from the temporary directory to the output directory but rename
# them to "res-0", "res-1", etc.
for i in $(seq 0 4); do
    mv $TMP_DIR/cluster*-$i/test_execution.json "$OUTPUT_DIR/res-$i.json"
done

rm -rf "$TMP_DIR"
