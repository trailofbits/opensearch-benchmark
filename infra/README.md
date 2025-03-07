# OpenSearch Benchmarking Infrastructure

## Setup
### Environment Setup
- Install `terraform`
- Install AWS CLI
- In the AWS Console, go to "Security Credentials" and create a new "Access Key"
- Set the environment variables `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY`
- Copy `terraform.tfvars.example` to `terraform.tfvars`.
- Configure `terraform.tfvars`. Common variables to configure are:
  - `aws_region`, `aws_subnet_zone`: Specify where AWS infrastructure is deployed
  - `target_cluster_type`: Cluster to benchmark, either OpenSearch or ElasticSearch
  - `prefix_list_id`, `prefix_list_region`: See Prefix List under Resource Setup.
  - `snapshot_user_aws_access_key_id`: See Snapshot S3 Bucket under Resource Setup
  - `snapshot_user_aws_secret_access_key`: See Snapshot S3 Bucket under Resource Setup
  - `benchmark_environment`: Environment metadata tag for results in data store
  - `datastore_host`, `datastore_username`, `datastore_password`: See Data Store under Resource Setup
  - `s3_bucket_name`: See Snapshot S3 Bucket under Resource Setup
  - `workload`: Name of workload to run
  - `workload_params`: Parameters to configure a workload. See the `workload_params_default/` directory for standard parameters for each workload.
- `terraform workspace new <unique-name>` (e.g. `terraform workspace new rschirone`)
- `terraform init`
- Note: The data store credentials and cluster password will be saved to the load generation machine.

### Resource Setup
The following resources are not provisioned by terraform and must be created beforehand:
- Data store
- Snapshot S3 bucket
- (Optional) Prefix list
#### Data Store
OpenSearch Benchmark will automatically upload benchmark results to a shared metric data store that is an OpenSearch deployment.

After you create an OpenSearch deployment to store results, you need to update the following terraform variables:
- `datastore_host`: Data store host
- `datastore_username`: Username to access data store
- `datastore_password`: Password to access data store

If you want to disable uploading to the shared data store, edit `/mnt/.benchmark/benchmark.ini` to use the commented default config for `[results_publishing]`. This will save results locally on the benchmark machine.
#### Prefix List
You can optionally add the load generation machine to a [prefix list](https://docs.aws.amazon.com/vpc/latest/userguide/managed-prefix-lists.html) for IP-based access control to the data store. The prefix list resource must exist before deploying with terraform. Terraform will add the load generation IP to the prefix list, so that the benchmarking client can upload results to the data store.

To use a prefix list:
  - Set `prefix_list_id` to the prefix list's ID.
  - Set `prefix_list_region` to the prefix list's region.
  - The workspace name is used as a description for the prefix list entry

If you don't want to use a prefix list, you don't need to set `prefix_list_id` nor `prefix_list_region`.
#### Snapshot S3 Bucket
If you want to use snapshots for OS and ES, create an AWS S3 bucket.

Create an AWS S3 bucket with default settings. Then, create a `snapshot-user` to access the bucket.

Next, give the user access to the bucket by creating the following IAM policy and associating it with the user:
```
{
	"Statement": [
		{
			"Action": [
				"s3:ListBucket",
				"s3:GetBucketLocation",
				"s3:ListBucketMultipartUploads",
				"s3:ListBucketVersions"
			],
			"Effect": "Allow",
			"Resource": [
				"arn:aws:s3:::snapshots-osb",
			]
		},
		{
			"Action": [
				"s3:GetObject",
				"s3:PutObject",
				"s3:DeleteObject",
				"s3:AbortMultipartUpload",
				"s3:ListMultipartUploadParts"
			],
			"Effect": "Allow",
			"Resource": [
				"arn:aws:s3:::snapshots-osb/*",
			]
		}
	],
	"Version": "2012-10-17"
}
```
Note: In this example policy, the bucket is named `snapshots-osb`.

Specify the following `terraform.tfvars` variables:
- `s3_bucket_name`:  S3 Bucket name
- `snapshot_user_aws_access_key_id`: `snapshot-user`'s access id
- `snapshot_user_aws_secret_access_key`: `snapshot-user`'s secret key

Here is some additional information on Snapshot Buckets for [ElasticSearch](https://www.elastic.co/guide/en/elasticsearch/reference/current/repository-s3.html) and [OpenSearch](https://opensearch.org/docs/latest/tuning-your-cluster/availability-and-recovery/snapshots/index/).

## Usage
Run `terraform apply` to deploy infrastructure.

To specify alternative workloads/parameters, you can run:
  - `terraform apply -var="workload=pmc" -var="workload_params=$(cat workload_params_default/pmc.json)"`
  - or`terraform apply -var-file=my-terraform.tfvars` if you have a different `tfvars` file.

The Terraform script is going to create several AWS EC2 instances. A `target-cluster` instance is used to host the product being benchmarked (e.g. OpenSearch). There may be additional cluster instances if the workload uses a multi-node deployment. A `load-generation` instance runs the OpenSearch Benchmark tool used to load data and perform queries to the target cluster.

Use `terraform output` to get the IPs/hostnames of the instances.

Use `terraform output cluster-password` to get the password for the cluster.

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

See the `scripts/report-gen` [README](scripts/report-gen/README.md) for more detail.

## Results Metadata
Comprehensive metadata is saved with the results in the data store. The metadata includes custom tags, built-in fields, and profiling information.

The metadata scheme is explained here: [results_metadata.md](results_metadata.md)

## Identify AWS Resources in Use

```shell
./scripts/resources.sh
```
