# Usage

The scripts downloads batches of benchmark results from an OpenSearch datastore.  
It creates one csv per batch, with the naming format of `<run-group>-<engine>-<engine version>-<workload>-<test-procedure>.csv`.
The `run-group` format is `YYYY-MMMM-DDThhmmssZ`, where `T` and `Z` are literal.

To properly authenticate with the datastore, you need to provide the datastore password in the `DS_PASSWORD` environment variable.
Use `poetry run benchmark_results_downloader --help` for a complete list of options.

## Prerequisites

1. Install `poetry`
2. Run `poetry install` in the root of the project folder

## Download benchmark data from a date until now

`poetry run benchmark_results_downloader --host <host> --benchmark_data <output_folder> --from 2024-10-01`

## Download benchmark data in a date range

`poetry run benchmark_results_downloader --host <host> --benchmark_data <output_folder> --from 2024-10-01 --to 2024-10-05`

## Download benchmark data from different sources

Use the `--source` option and use any combination of the available choices. Default is all scheduled runs.

NOTE: The user tag is `user-tags.ci` and currently `ci-scheduled = scheduled`, `ci-manual = manual` and `other = not-used or ""`

### Only CI scheduled runs:

`poetry run benchmark_results_downloader [...] --source ci-scheduled`

### All CI runs:
`poetry run benchmark_results_downloader [...] --source ci-scheduled ci-manual`

### All non-CI runs:
`poetry run benchmark_results_downloader [...] --source other`
