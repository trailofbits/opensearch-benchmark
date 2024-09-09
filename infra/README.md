# OpenSearch benchmarking infrastructure

## Create your own environment for benchmarking
- Install `terraform` and `awscli`.
- In the AWS Console, go to "Security Credentials" and create a new "Access Key"
- Set the environment variables `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY`
- `terraform workspace new <unique-name>` (e.g. `terraform workspace new rschirone`)
- `terraform init`
- `terraform apply -var ssh_pub_key=~/.ssh/id_rsa.pub` (or change the variable in `terraform.tfvars` and just run `terraform apply`)
- connect to the VM with `ssh ubuntu@<ip>`

The Terraform script is going to create two separate AWS EC2 instances, one
`target-cluster` used to host the product being benchmarked (e.g. OpenSearch)
and the other `load-generation` running OpenSearch Benchmarking tool, used to
load data and perform queries to the target cluster.

## Target product configuration (target-cluster host)

### OpenSearch
TODO

### ElasticSearch
#### Deployment from scratch
Copy the `scripts/es_cluster.sh` script in the `target-cluster` instance and run
it to install and configure ElasticSearch. The script will display the password
for the `elastic` user on the cluster and it will write it into `/mnt/.es_pwd`.

#### Deployment from existing Snapshot
TODO

## OpenSearch Benchmarking configuration (load-generation host)
Copy the `scripts/es_indexes` directory and the `scripts/es_load_generation.sh`
script in the `load-generation` instance and run it to install OpenSearch
Benchmark and configure it to run the benchmark against ElasticSearch.

Run it like this:
```shell
./es_load_generation.sh https://ec2-100-26-242-217.compute-1.amazonaws.com:9200 elastic <password>
```
