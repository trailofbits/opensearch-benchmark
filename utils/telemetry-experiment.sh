#!/bin/bash
# Repeatedly run benchmark on instance, alternating with telemetry enabled/disabled
# Usage (from infra dir): scp -i $(terraform output -raw ssh_private_key_file) ../utils/telemetry-experiment.sh ubuntu@$(terraform output -raw load-generation-ip):/home/ubuntu/
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

    echo "[$BATCH_TIME] [telemetry on] Restoring snapshot" | tee "$LOGFILE"
    bash /mnt/restore_snapshot.sh

    echo "[$BATCH_TIME] [telemetry on] Running benchmark" | tee "$LOGFILE"
    TELEMETRY_DEVICES="node-stats" bash /mnt/benchmark.sh dev

    echo "[$BATCH_TIME] [telemetry off] Restoring snapshot" | tee "$LOGFILE"
    bash /mnt/restore_snapshot.sh

    echo "[$BATCH_TIME] [telemetry off] Running benchmark" | tee "$LOGFILE"
    TELEMETRY_DEVICES="" bash /mnt/benchmark.sh dev

    echo "[$BATCH_TIME] Completed batch" | tee "$LOGFILE"

    echo "[$BATCH_TIME] Waiting for 5 minutes..." | tee "$LOGFILE"
    sleep 300
done
