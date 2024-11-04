# Report Generator


## Quickstart

Use `download_nightly.sh` to download nightly benchmark data.

```shell
./download_nightly.sh 2024-10-21 2024-10-29
```

Results will be downloaded to a directory named `download_nightly-{start_date}-{end_date}`.

Creating a report will require a google API credentials file. 
Follow the Follow the [Python quickstart guide for the Google Workspace API](https://developers.google.com/docs/api/quickstart/python) tutorial to create one.
Make sure to enable Google Docs/Spreadsheet access in the scopes.

From then on, use `create_report.sh` to create a google spreadsheet report from the generated data.

```shell
./create_report.sh download_nightly_2024-10-21_2024-10-29/ /path/to/credentials.json
```

## Google Credentials