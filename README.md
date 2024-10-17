# amazon-benchmark
OpenSearch: Artifacts related to benchmarking, including documentation, benchmarking harness source code and benchmarking results.

## Using `plots.ipynb`

1. (Optional) Create and activate a new Python virtual environment: `python3 -m venv .venv; source .venv/bin/activate`
2. Install the dependencies `pip install -r requirements.txt`
3. Place the latest sqlite database in the same directory as the notebook (`amz_benchmark_data_20241015.sqlite`)
4. Run the notebook -- VSCode works well for this.

Multiple run groups can be plotted simultaneously, they will be distinguished by color in the final graph.
The most recent and reliable run groups are the ones marked `dev gh-nightly-*`.

## Querying the raw data

The database containing the raw data can be queried from any client supporting SQLite, and follows the following schema (only the relevant fields are shown):

```sql
CREATE TABLE "runs" (
  "id",
  "environment",
  "workload",
  "distribution_version",
  "run_group",
  "engine_type",
  "run_type",
  PRIMARY KEY("id")
);

CREATE TABLE "service_time" (
  "id",
  "run_id",
  "task",
  "sample_type",
  "value",
  PRIMARY KEY("id")
);
```

As an example, this is the query to extract all of the OS samples regarding the `range-auto-date-histo` big5 task from the nightly runs:

```sql
SELECT runs.run_group, service_time.value
FROM runs JOIN service_time ON runs.id = service_time.run_id
WHERE
    runs.workload = 'big5' AND
    service_time.task = 'range-auto-date-histo' AND
    runs.engine_type = 'OS' AND
    runs.environment LIKE 'gh-nightly-%';
```
