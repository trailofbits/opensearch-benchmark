# OpenSearch benchmarking infrastructure

## Create your own environment for benchmarking

- Install `terraform`.
- Install AWS CLI
- In the AWS Console, go to "Security Credentials" and create a new "Access Key"
- Set the environment variables `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY`
- Copy `terraform.tfvars.template` to `terraform.tfvars`.
  - For configurations for each workload, see `terraform_tfvars/` directory
- `terraform workspace new <unique-name>` (e.g. `terraform workspace new rschirone`)
- `terraform init`
- Modify the `terraform.tfvars` file according to your needs
- Note: The data store credentials and cluster password will be saved to the load generation machine.
- By default, the load generation IP is added to the [shared prefix list](https://us-east-1.console.aws.amazon.com/vpcconsole/home?region=us-east-1#PrefixListDetails:prefixListId=pl-06f77c0b59dbf70fe) (id: `pl-06f77c0b59dbf70fe`). This gives access to the shared data store.
  - The workspace name is used a description for the prefix list entry
- Run `terraform apply`

The Terraform script is going to create two separate AWS EC2 instances, one `target-cluster` used to host the product being benchmarked (e.g. OpenSearch) and the other `load-generation` running OpenSearch Benchmarking tool, used to load data and perform queries to the target cluster.

Use `terraform output` to get the IPs/hostnames of the two instances.

Use `terraform output cluster-password` to get the password for the cluster.

### Snapshotting

If you want to use snapshotting, configure an S3 bucket on AWS and access to it. For ElasticSearch, follow the instructions in [here](https://www.elastic.co/guide/en/elasticsearch/reference/current/repository-s3.html). For OpenSearch, follow the instructions [here](https://opensearch.org/docs/latest/tuning-your-cluster/availability-and-recovery/snapshots/index/).

### Connecting to the Metric Datastore

OpenSearch Benchmark will automatically upload benchmark results to the shared metric data store. The data store-relevant terraform variables are:

- `benchmark_environment`: Metadata tag for the results
- `datastore_host`, `datastore_username`, `datastore_password`: Required to connect to the data store.

If you want to disable uploading to the shared data store, edit `/mnt/.benchmark/benchmark.ini` to use the commented default config for `[results_publishing]`. This will save results locally.

## Ingest/Load the data

Connect to the load-generation host with:

```shell
ssh -i $(terraform output -raw ssh_private_key_file) ubuntu@$(terraform output -raw load-generation-ip)
```

The default multiplexer is `byobu`. Here is a [cheatsheet](https://gist.github.com/devhero/7b9a7281db0ac4ba683f).

To ingest the data in the Target Cluster:

```shell
bash /mnt/ingest.sh
```

Alternatively, if you already have a snapshot and you want to restore it, do:

```shell
bash /mnt/restore_snapshot.sh
```

## Benchmark the queries

- Pass `official` or `dev` to tag the run results

```shell
bash /mnt/benchmark.sh [official|dev]
```

## Additional client options

To specify additional client options use the `EXTRA_CLIENT_OPTIONS` environment variable:

```shell
EXTRA_CLIENT_OPTIONS=timeout:240 bash /mnt/ingest.sh
```

## Get the results

From your local host:

```shell
mkdir /tmp/results
bash ./scripts/get_results.sh /tmp/results
```

You will get the JSON files of the various test executions in the `/tmp/results` directory.

## Destroy Instances

```shell
terraform destroy
```

## Segment timestamps

To extract lucene index segment timestamps, ssh into the load-generation host and run

```shell
bash /mnt/segment_timestamps.sh
```

This will produce a file named `segment-timestamps.txt` in the current directory.

## Upload Results to Google Sheets

```shell
python3 -m venv env
source env/bin/activate

(env) pip install poetry

(env) cd ./scripts/benchmark_results_downloader/
(env) poetry install
(env) ./download_nightly.sh
(env) ./download_versioned.sh

(env) cd ./scripts/report_generator/
(env) poetry install
(env) ./report_nightly.sh
(env) ./report_versioned.sh
