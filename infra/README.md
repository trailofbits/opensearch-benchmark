# OpenSearch benchmarking infrastructure

## Create your own environment for benchmarking
- Install `terraform`.
- In the AWS Console, go to "Security Credentials" and create a new "Access Key"
- Set the environment variables `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY`
- Create an Elastic IP in the console. This will be for the load generator so that it remains the same across deployments.
    - Go to the [Elastic IP page](https://us-east-1.console.aws.amazon.com/vpcconsole/home?region=us-east-1#Addresses:).
    - Select "Allocate Elastic IP Address"
    - Specify a network border group matching the region the infra will be deployed in.
    - Give it a Name by adding a new tag with key "Name"
- Add the Elastic IP you created to the shared prefix list.
    - This is to access the shared metric data store, which allows the CIDR blocks specified in the shared prefix list.
    - Go to the [shared prefix list](https://us-east-1.console.aws.amazon.com/vpcconsole/home?region=us-east-1#PrefixListDetails:prefixListId=pl-06f77c0b59dbf70fe) (id: `pl-06f77c0b59dbf70fe`).
    - Select "Modify Prefix List"
    - Select "Add New Entry"
    - Enter your Elastic IP address as a CIDR block (ending in /32) and give it a description.
- Set `load_gen_ip` to the Elastic IP address in `terraform.tfvars`.
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

## Connecting to the Metric Datastore
OpenSearch Benchmark can be configured to use a remote OpenSearch instance as a metric data store. These instructions are specific to the shared data store.

- Connect to the load generation instance and update `/mnt/.benchmark/benchmark.ini`
```
[results_publishing]
datastore.type = opensearch
datastore.host = insert_hostname_here
datastore.port = 443
datastore.secure = True
datastore.ssl.verification_mode = none
datastore.user = insert_user_here
datastore.password = insert_password_here
datastore.number_of_replicas = 1
datastore.number_of_shards = 3
```

## Ingest/Load the data

Connect to the load-generation host with:
```shell
ssh ubuntu@$(terraform output -raw load-generation-ip)
```

To ingest the data in the Target Cluster:

### ElasticSearch:
```shell
export ES_PASSWORD=<password>

bash /ingest.sh
```

Alternatively, if you already have a snapshot and you want to restore it, do:
```shell
export ES_PASSWORD=<password>

bash /restore_snapshot.sh
```

### OpenSearch:
```shell
export OS_VERSION=2.16.0
export OS_PASSWORD=<password>

bash ./ingest.sh
```

## Benchmark the queries.

### ElasticSearch:
```shell
export ES_PASSWORD=<password>

bash /benchmark.sh
```

### OpenSearch:
```shell
export OS_VERSION=2.16.0
export OS_PASSWORD=<password>

bash ./benchmark.sh
```

## Get the results
From your local host:
```shell
mkdir /tmp/results
bash ./scripts/get_results.sh /tmp/results
```

You will get the JSON files of the various test executions in the `/tmp/results`
directory.
