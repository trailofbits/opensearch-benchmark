# Setup

Setup instructions for Elasticsearch.

```shell
wget -qO - https://artifacts.elastic.co/GPG-KEY-elasticsearch | sudo gpg --dearmor -o /usr/share/keyrings/elasticsearch-keyring.gpg

sudo apt-get install apt-transport-https

echo "deb [signed-by=/usr/share/keyrings/elasticsearch-keyring.gpg] https://artifacts.elastic.co/packages/8.x/apt stable main" | sudo tee /etc/apt/sources.list.d/elastic-8.x.list

sudo apt-get update && sudo apt-get install elasticsearch

export ELASTIC_PASSWORD="your_password"

sudo /usr/share/elasticsearch/bin/elasticsearch-reset-password -u elastic

In elasticsearch.yml:
action.auto_create_index: .monitoring*,.watches,.triggered_watches,.watcher-history*,.ml*

sudo systemctl daemon-reload
sudo systemctl enable elasticsearch.service

sudo systemctl start elasticsearch.service

curl --cacert /etc/elasticsearch/certs/http_ca.crt -u elastic:$ELASTIC_PASSWORD https://localhost:9200 

export ES_JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64/

```

* Initialize environment

  ```shell
  sudo ./scripts/init.sh
  export ES_PASSWORD="<custom-admin-password>"
  ```

* Test and Run small benchmark **TODO**: because we don't yet have a custom index file for this yet.

  ```shell
  ./scripts/percolator_es_test.sh
  ./scripts/percolator_es_run.sh
  ```

* Test Benchmarks

  ```shell
  cp big5_index_es.json ~/.benchmark/benchmarks/workloads/default/big5/index.json
  ./scripts/big5_es_test.sh
  ```
