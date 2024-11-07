# Report Generator

## Setup

```shell
make dev
source env/bin/activate
```

Creating a report will require a google API credentials file. Follow the Python [quickstart guide](https://developers.google.com/docs/api/quickstart/python) for the Google Workspace API tutorial to create one. Make sure to enable Google Docs/Spreadsheet access in the scopes.

If you see `Authentication has failed`, just delete `token.json` and run the script again.

## Generate Nightly Report

Use `download_nightly.sh` to download nightly benchmark data.

```shell
./download_nightly.sh 2024-10-21 2024-10-29
```

Results will be downloaded to a directory named `download_nightly-{start_date}-{end_date}`.

From then on, use `create_report.sh` to create a google spreadsheet report from the generated data.

```shell
./create_report.sh download_nightly_2024-10-21_2024-10-29/ /path/to/credentials.json
```

Check your Google Drive home folder for the generated spreadsheet, or click the link outputted to the commandline.

## Generate ES Version Report

```shell
./download_versioned.sh 2024-10-21 2024-10-29

./create_report.sh download_versioned_2024-10-21_2024-10-29/ /path/to/credentials.json
```
