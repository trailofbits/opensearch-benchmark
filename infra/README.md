# OpenSearch Benchmarking Infrastructure

## Setup
- Install `terraform`
- Install AWS CLI
- In the AWS Console, go to "Security Credentials" and create a new "Access Key"
- Set the environment variables `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY`
- Copy `terraform.tfvars.example` to `terraform.tfvars`.
  - To configure a specific workload:
    - Set `workload` to the workload's name
    - Set `workload_params` to the contents of the workload's configuration file in the `workload_params_default/` directory.
- `terraform workspace new <unique-name>` (e.g. `terraform workspace new rschirone`)
- `terraform init`
- Modify the `terraform.tfvars` file according to your needs
- Note: The data store credentials and cluster password will be saved to the load generation machine.
- By default, the load generation IP is added to the [shared prefix list](https://us-east-1.console.aws.amazon.com/vpcconsole/home?region=us-east-1#PrefixListDetails:prefixListId=pl-06f77c0b59dbf70fe) (id: `pl-06f77c0b59dbf70fe`). This gives access to the shared data store.
  - If you are using a different prefix list, set `prefix_list_id` to the prefix list's ID.
  - The workspace name is used as a description for the prefix list entry
- Run `terraform apply` or `terraform apply -var="workload=pmc" -var="workload_params=$(cat workload_params_default/pmc.json)"` if you want to specify alternative workloads/parameters.
  - You can also run `terraform apply -var-file=my-terraform.tfvars` if you have a different `tfvars` file.

The Terraform script is going to create several AWS EC2 instances. A `target-cluster` instance is used to host the product being benchmarked (e.g. OpenSearch). There may be additional cluster instances if the workload uses a multi-node deployment. A `load-generation` instance runs the OpenSearch Benchmark tool used to load data and perform queries to the target cluster.

Use `terraform output` to get the IPs/hostnames of the instances.

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
This will run the workload specified in the `terraform.tfvars` several times to perform a full benchmark "test".

Pass `official` or `dev` to tag the run results

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

### Setup
Install python >= 3.13 and [uv](https://docs.astral.sh/uv/).

You will also need a Google API credentials file. Follow the steps below:
  1. [Create a project](https://developers.google.com/workspace/guides/create-project)
  2. [Enable APIs](https://developers.google.com/workspace/guides/enable-apis). Search for and enable the Google Sheets API
  3.  [Configure OAuth Consent](https://developers.google.com/workspace/guides/configure-oauth-consent). Select "Internal" for the user type.
  4. [Create OAth client ID credentials](https://developers.google.com/workspace/guides/create-credentials#oauth-client-id).
  5. Download the created credentials file.

Lastly you will need the URL and password for the shared data store.

### Generate Report

The script `./scripts/generate_report.sh` will download all results from scheduled CI runs, create and upload a google sheet report.

It expects the data store URL and password to be in the `DS_URL` and `DS_PASSWORD` environment variables. It takes a date range as input in the form `YYY-MM-DD YYYY-MM-DD` and a path to the google credentials file.

```shell
export DS_URL=<datastore url>
export DS_PASSWORD=<datastore password>
./scripts/generate_report.sh 2024-10-10 2024-11-10 /path/to/credentials.json
```

The above will generate a report with results from October 10th 2024 to November 10th 2024 and print the url for the generated google sheet.

See the `scripts/report-gen` [README](scripts/report-gen/README.md) for more detail.
