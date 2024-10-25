#!/bin/bash
# Repeatedly run benchmark on instance
# Usage (from infra dir): scp ../utils/benchmark-loop.sh ubuntu@$(terraform output -raw load-generation-ip):/home/ubuntu/
set -ex

# Check if directory argument is provided
if [ $# -eq 0 ]; then
    echo "Please provide a directory to store output files."
    echo "Usage: $0 <output_directory>"
    exit 1
fi

BASE_OUTPUT_DIR="$1"

# Create the base output directory if it doesn't exist
mkdir -p "$BASE_OUTPUT_DIR"

while true; do
    # Get current timestamp for this batch
    BATCH_TIME=$(date +"%Y-%m-%dT%H-%M-%S")
    BATCH_DIR="$BASE_OUTPUT_DIR/batch-$BATCH_TIME"
    LOGFILE="$BATCH_DIR/summary.log"

    # Create the batch directory
    mkdir -p "$BATCH_DIR"

    echo "[$BATCH_TIME] Starting batch" | tee "$LOGFILE"

    echo "[$BATCH_TIME] Restoring snapshot" | tee "$LOGFILE"
    bash /restore_snapshot.sh

    echo "[$BATCH_TIME] Running benchmark" | tee "$LOGFILE"
    bash /benchmark.sh dev

    echo "[$BATCH_TIME] Completed batch" | tee "$LOGFILE"

    # Wait for 10 minutes (300 seconds)
    echo "[$BATCH_TIME] Waiting for 10 minutes..." | tee "$LOGFILE"
    sleep 600
done
