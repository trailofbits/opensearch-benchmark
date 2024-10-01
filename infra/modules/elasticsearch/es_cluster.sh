#!/bin/bash

CLUSTER_PASSWORD=$1
CLUSTER_VERSION=$2
ES_SNAPSHOT_AWS_ACCESS_KEY_ID=$3
ES_SNAPSHOT_AWS_SECRET_ACCESS_KEY=$4

cd /mnt || exit 1

# Install ElasticSearch from .tar.gz
wget https://artifacts.elastic.co/downloads/elasticsearch/elasticsearch-$CLUSTER_VERSION-linux-x86_64.tar.gz
wget https://artifacts.elastic.co/downloads/elasticsearch/elasticsearch-$CLUSTER_VERSION-linux-x86_64.tar.gz.sha512
shasum -a 512 -c elasticsearch-$CLUSTER_VERSION-linux-x86_64.tar.gz.sha512
tar -xzf elasticsearch-$CLUSTER_VERSION-linux-x86_64.tar.gz
cd elasticsearch-$CLUSTER_VERSION/ || exit 1

cat <<EOF > config/elasticsearch.yml
discovery.type: single-node
network.host: 0.0.0.0
path.repo: ["/mnt/es-backup"]
path.data: /mnt/es-data
path.logs: /mnt/es-logs
EOF

sudo mkdir /mnt/es-backup && sudo chmod ugo+rwx /mnt/es-backup
sudo mkdir /mnt/es-data && sudo chmod ugo+rwx /mnt/es-data
sudo mkdir /mnt/es-logs && sudo chmod ugo+rwx /mnt/es-logs

echo "$ES_SNAPSHOT_AWS_ACCESS_KEY_ID" | ./bin/elasticsearch-keystore add -s -f -x s3.client.default.access_key
echo "$ES_SNAPSHOT_AWS_SECRET_ACCESS_KEY" | bin/elasticsearch-keystore add -s -f -x s3.client.default.secret_key

# Start Elasticsearch
./bin/elasticsearch -d -p /mnt/es_pid

# Wait for Elasticsearch to start
while ! curl --max-time 5 -ks https://localhost:9200 > /dev/null 2>&1 ; do
    echo "Waiting for Elasticsearch to start"
    sleep 1
done 

# Reset password to a known value
CURRENT_ELASTIC_PASSWORD=$(./bin/elasticsearch-reset-password -u elastic -b -s)
curl -ku elastic:$CURRENT_ELASTIC_PASSWORD https://localhost:9200

echo "Current: $CURRENT_ELASTIC_PASSWORD , New: $CLUSTER_PASSWORD"

curl -k -X POST "https://localhost:9200/_security/user/elastic/_password" -u elastic:$CURRENT_ELASTIC_PASSWORD -H "Content-Type: application/json" -d "{
  \"password\": \"$CLUSTER_PASSWORD\"
}"

curl -ku elastic:$CLUSTER_PASSWORD https://localhost:9200
