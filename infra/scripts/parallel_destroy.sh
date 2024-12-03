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
    terraform destroy -auto-approve \
            "${param_aws[@]}" \
            &> "destroy_${prefix}-${i}.log" &
    sleep 30
done
