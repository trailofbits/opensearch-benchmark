#!/bin/bash

# Fix OSB to be compatible to pass extra OS KNN API parameters
OSB_INSTALL_DIR="$(pip list -v | grep opensearch-benchmark | awk '{print $3}')"
PATCH_FILE="/os_files/osb-1.12.0-knn.patch"
patch -p1 -d "$OSB_INSTALL_DIR" < "$PATCH_FILE"

# Fix OSB vectorsearch workload to pass extra OS KNN API parameters
OSB_WORKLOAD_DIR="/mnt/.osb/benchmarks/workloads/default"
PATCH_FILE="/os_files/vectorsearch-task-1.12.0.patch"
patch -p1 -d "$OSB_WORKLOAD_DIR" < "$PATCH_FILE"
