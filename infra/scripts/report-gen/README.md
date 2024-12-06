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

Check your Google Drive home folder for the generated spreadsheet, or click the link outputted to the command line.

## Generate ES Version Report

Assuming ES versioned runs are executed manually via the CI.

```shell
./download_manual.sh 2024-10-21 2024-10-29

./create_report.sh download_manual_2024-10-21_2024-10-29/ /path/to/credentials.json
```


## Tests

Running `make test` will run a snapshot test by creating a new spreadsheet from a fixed dataset (`test/data/test_data`) and comparing the generated spreadsheet to previously generated sheets (`test/data/results.csv` and `test/data/summary.csv`).

To run the test, the environment variable `GOOGLE_CRED` should contain the path to the `credentials.json` created above.

The snapshot test only checks that existing behavior is not broken. When modifying the generated sheet you should:

    1. Modify the test to exclude the modifications.
    2. Pass all other tests, ensuring no existing features were broken.
    3. Verify the new features are working correctly.
    4. Update the data and snapshots in `test/data` with the new ground truth.

Ground truth csv's can be downloaded from google drive directly (File -> download -> csv).
