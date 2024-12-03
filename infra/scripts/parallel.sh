#!/usr/bin/env bash

if [ -z "$DS_PASSWORD" ]; then
    echo "DS_PASSWORD is not set"
    exit 1
fi
if [ -z "$AWS_ACCESS_KEY_ID" ]; then
    echo "AWS_ACCESS_KEY_ID is not set"
    exit 1
fi
if [ -z "$AWS_SECRET_ACCESS_KEY" ]; then
    echo "AWS_SECRET_ACCESS_KEY is not set"
    exit 1
fi

if [ $# -ne 3 ]; then
    echo "Usage: $0 <OpenSearch|ElasticSearch> <version> <number_of_tests>"
    exit 1
fi

type="$1"
version="$2"
end="$3"

set -x

workload="big5"
prefix_list="pl-06f77c0b59dbf70fe"
region="us-east-1"
vpc="vpc-02f34b77a5acbb041"
subnet="subnet-09f4af500aa3636ba"
igw="igw-0e80421e85d2f29b5"
rtb="rtb-0a8649e2051df423e"
sg="sg-054e9eec3cfbfc068"

tasks="sort_numeric_desc_with_match,range_field_conjunction_small_range_big_term_query,sort_numeric_asc_with_match,sort_keyword_no_can_match_shortcut,sort_keyword_can_match_shortcut,range-agg-2"

today=$(date '+%Y-%m-%d')

prefix="${today}-${workload}-${type}-${version}"
start=1

param_aws=(
    -var="aws_region=${region}"
    -var="aws_subnet_zone=${region}a"
    -var="prefix_list_id=${prefix_list}"
    -var="vpc_id=${vpc}"
    -var="vpc_subnet_id=${subnet}"
    -var="vpc_gateway_id=${igw}"
    -var="vpc_route_table_id=${rtb}"
    -var="security_group_id=${sg}"
)

for ((i=start; i<=end; i++)); do
    terraform workspace select -or-create=true "${prefix}-${i}"
    terraform init

    param_cluster=(
        "${param_aws[@]}"
        -var="target_cluster_type=${type}"
        -var="snapshot_user_aws_access_key_id=AKIAYZZGTDYZ2YAJK6OE"
        -var="snapshot_user_aws_secret_access_key=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"
        -var="snapshot_version=${prefix}-${i}"
        -var="benchmark_environment=${prefix}-${i}"
        -var="datastore_host=opense-clust-AEqAZh9qc4u7-dcbe5cce2775e15e.elb.us-east-1.amazonaws.com"
        -var="datastore_username=admin"
        -var="datastore_password=${DS_PASSWORD}"
        -var="workload=${workload}"
        -var="workload_params={\"number_of_replicas\": 0,\"bulk_indexing_clients\": 1,\"target_throughput\": 0}"
    )

    terraform apply -auto-approve \
        "${param_cluster[@]}" \
        -var="os_version=${version}" \
        -var="es_version=${version}" \
        &> "out_$prefix-$i.log" &

    sleep 30
done

for ((i=start; i<=end; i++)); do
    terraform workspace select "$prefix-$i"
    while [ "$(terraform output -raw load-generation-ip)" == "" ]; do
        sleep 10
    done
    ssh \
        -o StrictHostKeyChecking=no \
        -o ServerAliveInterval=60 \
        -o ServerAliveCountMax=10 \
        -o IdentitiesOnly=yes \
        -i "$(terraform output -raw ssh_private_key_file)" \
        "ubuntu@$(terraform output -raw load-generation-ip)" -tt -- "exit 0" || exit 1
done

for ((i=start; i<=end; i++)); do
    terraform workspace select "$prefix-$i"
    key="$(terraform output -raw ssh_private_key_file)"
    conn="ubuntu@$(terraform output -raw load-generation-ip)"
    ssh \
        -o StrictHostKeyChecking=no \
        -o ServerAliveInterval=60 \
        -o ServerAliveCountMax=10 \
        -o IdentitiesOnly=yes \
        -i "$key" \
        "$conn" -tt -- \
        "bash -ixc \"FORCE_INGESTION=true EXTRA_CLIENT_OPTIONS=timeout:240 CI_TAG=dev bash -ix /mnt/ingest.sh && EXTRA_CLIENT_OPTIONS=timeout:240 RUN_GROUP_ID=benchmark-$today-$workload CI_TAG=dev bash -x /mnt/benchmark.sh dev '$tasks'\"" \
        &> "ssh_out_$prefix-$i.log" &
done

