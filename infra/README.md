# OpenSearch benchmarking infrastructure

## Create your own environment for benchmarking
- Install `terraform`.
- In the AWS Console, go to "Security Credentials" and create a new "Access Key"
- Set the environment variables `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY`
- `terraform workspace new <unique-name>` (e.g. `terraform workspace new rschirone`)
- `terraform init`
- Modify the `terraform.tfvars` file according to your needs
- Run `terraform apply`

The Terraform script is going to create two separate AWS EC2 instances, one
`target-cluster` used to host the product being benchmarked (e.g. OpenSearch)
and the other `load-generation` running OpenSearch Benchmarking tool, used to
load data and perform queries to the target cluster.

Use `terraform output` to get the IPs/hostnames of the two instances.
Use `terraform output cluster-password` to get the password for the cluster.

### Snapshotting
If you want to use snapshotting, configure an S3 bucket on AWS and access to it. For ElasticSearch, follow the instructions in [here](https://www.elastic.co/guide/en/elasticsearch/reference/current/repository-s3.html).

## Run the benchmarking

Connect to the load-generation host with:
```shell
ssh ubuntu@$(terraform output -raw load-generation-ip)
```

To ingest the data in the Target Cluster:
```shell
export ES_HOST=https://<hostname>.amazonaws.com:9200
export ES_PASSWORD=<password>

bash /ingest.sh
```

To benchmark the queries:
```shell
export ES_HOST=https://<hostname>.amazonaws.com:9200
export ES_PASSWORD=<password>

bash /benchmark.sh
```
