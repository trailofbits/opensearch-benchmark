CLUSTER_HOST=$1
WORKLOAD=$2
OPENSEARCH_VERSION=2.16.0
RESULTS_OUTPUT_PATH=/mnt/opensearch-bench/results
TEST_EXECUTION_ID="test_$(date '+%Y_%m_%d_%H_%M_%S')"
RESULTS_FILE="$RESULTS_OUTPUT_PATH/$TEST_EXECUTION_ID"

if [ -z "$CLUSTER_HOST" ]; then
    echo "Please specify the cluster host address"
    exit 1
fi

if [ -z "$WORKLOAD" ]; then
    echo "Please specify the workload name"
    exit 1
fi

mkdir $RESULTS_OUTPUT_PATH


read -s -p "Please enter the open search password: " password

echo "Results folder $RESULTS_OUTPUT_PATH. Test id: $TEST_EXECUTION_ID"

# Make the OpenSearch Benchmark available on the path
export PATH=$PATH:$HOME/.local/bin

# Benchmark directory
export BENCHMARK_HOME=/mnt/opensearch-bench


# Download dataset
echo "Download dataset"
opensearch-benchmark execute-test \
--kill-running-processes \
--pipeline=benchmark-only \
--workload=$WORKLOAD \
--target-hosts=$CLUSTER_HOST \
--workload-params="number_of_replicas:0,bulk_indexing_clients:1,max_num_segments:10" \
--client-options="basic_auth_user:'admin',basic_auth_password:'$password',use_ssl:true,verify_certs:false" \
--distribution-version=$OPENSEARCH_VERSION \
--test-mode


# Ingest workload
echo "Ingest workload"
opensearch-benchmark execute-test \
--pipeline=benchmark-only \
--workload=$WORKLOAD \
--target-hosts=$CLUSTER_HOST \
--workload-params="number_of_replicas:0,bulk_indexing_clients:1,max_num_segments:10" \
--client-options="basic_auth_user:'admin',basic_auth_password:'$password',use_ssl:true,verify_certs:false" \
--kill-running-processes \
--results-file=$RESULTS_FILE-ingest \
--test-execution-id=$TEST_EXECUTION_ID \
--distribution-version=$OPENSEARCH_VERSION \
--exclude-tasks="type:search"


exit 0


WORKLOAD_PARAMS="\"number_of_replicas:0,bulk_indexing_clients:1,force_merge_max_num_segments:t,max_num_segments:10\""
CLIENT_OPTIONS="\"basic_auth_user:'admin',basic_auth_password:'$password',use_ssl:true,verify_certs:false\""

# Queries only
echo "Running Queries Only"
for i in 2 3 4 5
do
opensearch-benchmark execute-test --pipeline=benchmark-only --workload=$WORKLOAD  --target-hosts=$CLUSTER_HOST --workload-params=$WORKLOAD_PARAMS --kill-running-processes --include-tasks="\"type:search\"" --results-file=$RESULTS_FILE-$i --test-execution-id=$TEST_EXECUTION_ID-$i --distribution-version=8.0.0

echo "Sleeping for 60 seconds"
sleep 60

done




