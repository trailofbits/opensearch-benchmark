#!/bin/bash

OUTPUT_DIR=$1

for i in $(seq 0 3)
do
    scp "ubuntu@$(terraform output -raw load-generation-ip):/mnt/.benchmark/benchmarks/test_executions/es-query-benchmark-$i/test_execution.json" \
        $OUTPUT_DIR/res-$i.json
done
