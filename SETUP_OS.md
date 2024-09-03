# Setup

## Notes

* Make sure your machine is compatible with their [OS requirements](https://opensearch.org/docs/latest/install-and-configure/os-comp/).
  * **NOTE**: There is no support for macOS.
  * Set up a Coder instance (e.g., `n2-standard-4`) with 250GB of disk space.
* You can install OSB via pip.
  * Make sure you have 3.8 <= Python <= 3.10

* ```shell
  sudo apt install python3-venv

  python3 -m venv env
  source env/bin/activate
  (env) python -m pip install --upgrade pip

  # Install opensearch benchmark
  (env) pip install opensearch-benchmark
  (env) opensearch-benchmark -h

  sudo apt install openjdk-17-jdk-headless
  update-alternatives --list java
  export JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64/

  sudo sysctl -w vm.max_map_count=262144
  sudo sysctl -p

  # Install opensearch (might not be needed)
  sudo apt-get update && sudo apt-get -y install lsb-release ca-certificates curl gnupg2
  curl -o- https://artifacts.opensearch.org/publickeys/opensearch.pgp | sudo gpg --dearmor --batch --yes -o /usr/share/keyrings/opensearch-keyring
  echo "deb [signed-by=/usr/share/keyrings/opensearch-keyring] https://artifacts.opensearch.org/releases/bundle/opensearch/2.x/apt stable main" | sudo tee /etc/apt/sources.list.d/opensearch-2.x.list

  sudo apt update
  sudo apt list -a opensearch
  sudo env OPENSEARCH_INITIAL_ADMIN_PASSWORD=<custom-admin-password> apt-get install opensearch=2.16.0

  sudo systemctl daemon-reload
  sudo systemctl enable opensearch.service
  sudo systemctl start opensearch.service
  sudo systemctl status opensearch.service

  apt show opensearch

  curl -X GET https://localhost:9200 -u 'admin:<custom-admin-password>' --insecure
  curl -X GET https://localhost:9200/_cat/plugins?v -u 'admin:<custom-admin-password>' --insecure

  # Modify opensearch.yml: https://opensearch.org/docs/latest/install-and-configure/install-opensearch/debian/#step-3-set-up-opensearch-in-your-environment
  sudo systemctl restart opensearch

  # Test OSB (check for errors)
  (env) opensearch-benchmark execute-test --distribution-version=2.16.0 --workload=big5 --workload-params corpus_size:100,number_of_replicas:0,target_throughput:"" --test-mode

  # Update mapping file (not sure what this means yet)

  # Validate test: https://opensearch.org/docs/latest/benchmark/quickstart/#validating-the-test
  In the results returned by OpenSearch Benchmark, compare the workload.json file for your specific workload and verify that the document count matches the number of documents. For example, based on the percolator workload.json file, you should expect to see 2000000 documents in your cluster.

  vim ~/.benchmark/benchmarks/workloads/default/big5/workload.json
  curl -XGET "https://localhost:9200/_cat/indices?v" -u 'admin:<custom-admin-password>' --insecure

  # Run OSB for real
  (env) opensearch-benchmark execute-test --distribution-version=2.16.0 --workload=big5 --workload-params corpus_size:60,number_of_replicas:0,target_throughput:""

  # Snapshot the cluster

  # Run searches and Aggregate Results

  ```

* Initialize environment

  ```shell
  <kill es service. start os service.>
  sudo ./scripts/init.sh
  export OS_PASSWORD="<custom-admin-password>"
  ```

* Test and Run small benchmark

  ```shell
  ./scripts/percolator_os_test.sh
  ./scripts/percolator_os_run.sh
  ```

* Test Benchmarks

  ```shell
  ./scripts/big5_os_test.sh
  ```

* Run Benchmarks

  ```shell
  ./scripts/big5_os_run.sh
  ```
