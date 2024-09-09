#!/bin/bash

cd /mnt

wget https://artifacts.elastic.co/downloads/elasticsearch/elasticsearch-8.15.0-linux-x86_64.tar.gz
wget https://artifacts.elastic.co/downloads/elasticsearch/elasticsearch-8.15.0-linux-x86_64.tar.gz.sha512
shasum -a 512 -c elasticsearch-8.15.0-linux-x86_64.tar.gz.sha512
tar -xzf elasticsearch-8.15.0-linux-x86_64.tar.gz
cd elasticsearch-8.15.0/

cat <<EOF > config/elasticsearch.yml
discovery.type: single-node
network.host: 0.0.0.0 # set this as appropriate
path.repo: ["/mnt/es-backup"]
path.data: /mnt/es-data
path.logs: /mnt/es-logs
EOF

sudo mkdir /mnt/es-backup && sudo chmod ugo+rwx /mnt/es-backup
sudo mkdir /mnt/es-data && sudo chmod ugo+rwx /mnt/es-data
sudo mkdir /mnt/es-logs && sudo chmod ugo+rwx /mnt/es-logs

# Open ports on firewall
sudo ufw allow 9200/tcp
sudo ufw allow 9300/tcp

# Start Elasticsearch
./bin/elasticsearch &

# Wait for Elasticsearch to start
while ! curl -ks https://localhost:9200; do sleep 1; done 2>&1 >/dev/null

# Reset password to a known value
ELASTIC_PASSWORD=$(./bin/elasticsearch-reset-password -u elastic -b -s)
curl -ku elastic:$ELASTIC_PASSWORD https://localhost:9200

echo $ELASTIC_PASSWORD > /mnt/.es_pwd
