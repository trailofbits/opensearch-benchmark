# OpenSearch benchmarking infrastructure

## Create your own environment for benchmarking
- Install `terraform`.
- In the AWS Console, go to "Security Credentials" and create a new "Access Key"
- Set the environment variables `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY`
- `terraform workspace new <unique-name>` (e.g. `terraform workspace new rschirone`)
- `terraform init`
- Set/change variables in `terraform.tfvars` and run `terraform apply`

The Terraform script is going to create two separate AWS EC2 instances, one
`target-cluster` used to host the product being benchmarked (e.g. OpenSearch)
and the other `load-generation` running OpenSearch Benchmarking tool, used to
load data and perform queries to the target cluster.

Use `terraform output` to get the IPs/hostnames of the two instances.
Use `terraform output cluster-password` to get the password for the cluster.

## Run the benchmarking (load-generation host)
To ingest the data in the Target Cluster.
ElasticSearch:
```shell
export ES_HOST=https://<hostname>.amazonaws.com:9200
export ES_PASSWORD=<password>

bash ./ingest.sh
```
OpenSearch:
```shell
export OS_VERSION=2.16.0
export OS_PASSWORD=<password>

bash ./ingest.sh
```

To benchmark the queries.
ElasticSearch:
```shell
export ES_HOST=https://<hostname>.amazonaws.com:9200
export ES_PASSWORD=<password>

bash ./benchmark.sh
```
OpenSearch:
```shell
export OS_VERSION=2.16.0
export OS_PASSWORD=<password>

bash ./benchmark.sh
```
