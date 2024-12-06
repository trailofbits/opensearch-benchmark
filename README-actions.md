# OpenSearch Benchmarking Actions
You can run benchmarks automatically with Github Actions.

## Setup
You will need to set the following Github Secrets:
- `SNAPSHOT_AWS_ACCESS_KEY_ID`: AWS Access Key for accessing the Snapshot S3 Bucket
- `SNAPSHOT_AWS_SECRET_ACCESS_KEY`: AWS Secret Access Key for accessing the Snapshot S3 Bucket
- `DATASTORE_HOST`: Host of data store that benchmark results are uploaded to
- `DATASTORE_USERNAME`: Data store username
- `DATASTORE_PASSWORD`: Data store password
- `AWS_ACCESS_KEY_ID`: AWS Access Key to give Terraform permission to provision infrastructure
- `AWS_SECRET_ACCESS_KEY`: AWS Secret Access Key to give Terraform permission to provision infrastructure
- `SLACK_BOT_TOKEN`: Slack Bot Token to alert on failed nightly runs
- `SLACK_CHANNEL_ID`: Slack Channel ID to alert on failed nightly runs

You will need to set the following Github Variables:
- `DATASTORE_HOST`: Host of data store that benchmark results are uploaded to

## Run Benchmarks
There are two workflows for benchmarking:
- Ingest/Snapshot Workflows: Will ingest a new workload and save the snapshot to the S3 Bucket
- Nightly Benchmarks: Will run benchmarks
    - Before benchmarking, this workflow will restore the latest snapshot if it exists. If no snapshot exists, it will ingest the workload and make a snapshot.
### Ingest/Snapshot Workflows
- Parameters:
    - `Workloads to run`: Comma-separated list of workloads to run
    - `Overwrite workload parameters`: Overwrite parameters for specific workloads. All parameters will be overwritten for specified workloads.
        - Actions use default workload parameters defined in `infra/workload_params_default/`.
        - You can specify workloads with increasing granularity following: `workload[-cluster[-version]]`
        - See "How to modify jobs in CI" below for more.
    - `Cluster types`: Comma-separated list of clusters to run. Options are: OpenSearch and ElasticSearch
    - `Force snapshot creation`: Enabling will destroy the selected snapshot and recreate it.
    - `ElasticSearch versions`: Comma-separated list of ElasticSearch versions to test.
    - `Snapshot version`: Specify `latest` to use the latest snapshot. Specify `new` to create a new snapshot.
    - `OpenSearch versions`: Comma-separated list of OpenSearch versions to test.
    - `AWS region`: Region to deploy infrastructure in. A job can provision up to 12 deployments at a time, so be mindful of region resource limits.

### Nightly Benchmarks
- Parameters:
    - `Workloads to run`: See Ingest/Snapshot Workflows
    - `Overwrite workload parameters`: See Ingest/Snapshot Workflows
    - `Cluster types`: See Ingest/Snapshot Workflows
    - `Benchmark type`: Specify `official` or `dev` to tag the results in the data store. This is useful for reporting. Specify `dev` for development runs that shouldn't be in a report, and `official` for official runs.
    - `ElasticSearch versions`: See Ingest/Snapshot Workflows
    - `OpenSearch versions`:  See Ingest/Snapshot Workflows
    - `AWS region`: See Ingest/Snapshot Workflows

# How to modify jobs in CI

The `workload_params` argument can be used to overwrite the workload parameters
of a specific job. The user-specified parameters will overwrite all previously set parameter values for the workload

## Examples
### Overwrite parameters for all big5 workloads
```
{
    "big5": {
        "new_arg": "value"
    }
}
```

### Overwrite parameters for pmc on ES
```
{
    "pmc-es": {
        "new_arg": "value"
    }
}
```

### Overwrite parameters for pmc on ES but only on 8.15.0
```
{
    "pmc-es-8.15.0": {
        "new_arg": "value"
    }
}
```

### Overwrite parameters for big5 and pmc
```
{
    "pmc-es-8.15.0": {
        "new_arg": "value"
    },
    "big5": {
        "big5_param": "value2"
    }
}
```
