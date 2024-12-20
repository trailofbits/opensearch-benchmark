# Amazon Benchmark
Benchmark OpenSearch and ElasticSearch with the [OpenSearch Benchmark](https://github.com/opensearch-project/opensearch-benchmark) framework.

This project can automatically benchmark OpenSearch and ElasticSearch and report the results.

You can run benchmarks either manually or with Github Actions.

# Benchmarking Overview
This project can run the following [OpenSearch Benchmark workloads](https://github.com/opensearch-project/opensearch-benchmark-workloads):
- `big5`
- `noaa`
- `pmc`
- `nyc_taxis`
- `vectorsearch`
    - OpenSearch has 3 different "workload subtypes" for the three vectorsearch engines it supports:
        - nmslib
        - lucene
        - faiss
    - ElasticSearch only supports the lucene engine.
- `noaa_semantic_search`
    - This workload is OpenSearch-only, because ElasticSearch does not have the target benchmark features.

Running a benchmark has three main steps:
- Provision infrastructure with Terraform, including machine(s) for the cluster and a client machine.
- Prepare the cluster by ingesting a workload or restoring a snapshot
- Run the workload
    - This step excludes ingest-related operations in the workload due to the previous step.

Results from a benchmark are stored in a remote OpenSearch data store.

# Benchmark Manually
You can run a benchmark manually by deploying infrastructure with Terraform and running scripts on the benchmarking client machine.

To run a benchmark manually, see: [infra/README.md](infra/README.md)

# Benchmark with Github Actions
You can also run benchmarks with Github Actions. Actions automate all steps of a manual benchmark. Actions are configured to run nightly benchmarks.

To configure and run Github actions, see [README-actions.md](README-actions.md)

# View and Report Results
The results are stored in an OpenSearch data store automatically by OpenSearch Benchmark. There is information about how OpenSearch Benchmark configures the data store [here](https://opensearch.org/docs/latest/benchmark/reference/metrics/index/#opensearch).

You can view the results in the data store, or you can export them using our report generator. Our report generator will download results for a time range and create a summary report in Google Sheets.

To use our report generator, see [infra/scripts/report-gen/README.md](infra/scripts/report-gen/README.md).
