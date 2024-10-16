# Results Metadata
This document describes the metadata for results saved to the shared data store.

## User Tags
User tags are custom fields added to enrich the metadata. They are recorded in different fields depending on the index:
- `benchmark-results*`: `user-tags.<tag_name>`
- `benchmark-metrics*`: `meta.tag_<tag_name>`

| Tag Name | Description |
| -------- | -------- |
| run-group | Timestamp for a group of runs executed together with `scripts/benchmark.sh`. Serves as run group ID |
| engine-type | Cluster type. Either `OS` for OpenSearch or `ES` for ElasticSearch |
| arch | Architecture of cluster and load generation machines. |
| instance-type | AWS instance type of cluster and load generation machines |
| aws-account-id | AWS account ID which deployed the infrastructure |
| aws-loadgen-instance-id | AWS instance ID for the load generation machine |
| aws-cluster-instance-id | AWS instance ID for the cluster machine |
| aws-user-id | AWS IAM user that ran the benchmark |
| cluster-version | Version of the cluster |
| workload-distribution-version | Distribution version passed to OpenSearch-Benchmark and used to select the workload  |
| shard-count | Number of primary shards in the cluster index |
| replica-count | Number of replica shards for each primary shard  |
| run | Zero-indexed number for a run in a run group |
| run-type | Type of run. Options are `official`, `dev`, and `ingest` |
| snapshot-s3-bucket | S3 bucket storing the snapshot |
| snapshot-base-path | Snapshot base path in S3 bucket. Format: "cluster_type/cluster_version/workload/snapshot_version" |

- Explanation of `run-type` options:
    - `official`: Runs that should be included in reports (includes warmup runs)
    - `dev`: Runs executed during development. Can be ignored
    - `ingest`: Data ingestion runs. Can be ignored

## Built-in Fields
Built-in fields are created by OpenSearch Benchmark, but may have user-controlled input. This section describes key built-in fields for metadata.

| Field | Description |
| -------- | -------- |
| environment | Environment variable configured by the user which may describe the user or the run(s) being performed |
| test-execution-id | Unique identifier for a run. The format is `cluster-<run_group_timestamp>-<run_number>` |
| workload-params.* | Workload parameters configured explicitly via OpenSearch-Benchmark |
| workload | Workload being run |
| test-execution-timestamp | Timestamp of the run (different from run group timestamp)|
| benchmark-version | OpenSearch-Benchmark version |

## Profiling Fields
The [node-stats telemetry device](https://opensearch.org/docs/latest/benchmark/reference/telemetry/#node-stats) is enabled with default parameters.

The data it collects is stored in `benchmark-metrics*`, in records with name `node-stats`. See the [node stats API](https://opensearch.org/docs/latest/api-reference/nodes-apis/nodes-stats/) for more information on its fields.
