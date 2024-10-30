#!/bin/bash

ES_TF_WORKSPACE=$1
OS_TF_WORKSPACE=$2
OUTPUT_DIR=$3

run_ssh_cmd() {
    local host=$1
    local cmd=$2
    ssh -i "$(terraform output -raw ssh_private_key_file)" -t "ubuntu@$(terraform output -raw $host)" -- "bash -ic \"$cmd\""
}

run_load_generation_cmd() {
    local cmd=$1
    run_ssh_cmd load-generation-ip "$cmd"
}

run_target_cluster_cmd() {
    local cmd=$1
    run_ssh_cmd target-cluster-ip "$cmd"
}

cp_scp() {
    local src=$1
    local dest=$2
    scp -i "$(terraform output -raw ssh_private_key_file)" "$src" "ubuntu@$(terraform output -raw load-generation-ip):$dest"
}

download_file() {
    local host=$1
    local src=$2
    local dest=$3
    scp -i "$(terraform output -raw ssh_private_key_file)" "ubuntu@$(terraform output -raw $host):$src" "$dest"
}

queries="multi_terms-keyword"
for query in $queries ; do 
    terraform workspace select "$ES_TF_WORKSPACE"
    run_target_cluster_cmd "/mnt/async-profiler-3.0-linux-x64/bin/asprof start -f /mnt/flamegraph-$query.html \\\$(cat /mnt/pid)"
    run_load_generation_cmd "bash /mnt/benchmark.sh dev $query"
    run_target_cluster_cmd "/mnt/async-profiler-3.0-linux-x64/bin/asprof stop -f /mnt/flamegraph-$query.html \\\$(cat /mnt/pid)"
    download_file load-generation-ip "/mnt/flamegraph-$query.html" "$OUTPUT_DIR/flamegraph.$query.es.html"

    terraform workspace select "$OS_TF_WORKSPACE"
    run_target_cluster_cmd "/mnt/async-profiler-3.0-linux-x64/bin/asprof start -f /mnt/flamegraph-$query.html \\\$(cat /mnt/pid)"
    run_load_generation_cmd "bash /mnt/benchmark.sh dev $query"
    run_target_cluster_cmd "/mnt/async-profiler-3.0-linux-x64/bin/asprof stop -f /mnt/flamegraph-$query.html \\\$(cat /mnt/pid)"
    download_file load-generation-ip "/mnt/flamegraph-$query.html" "$OUTPUT_DIR/flamegraph.$query.os.html"
done


