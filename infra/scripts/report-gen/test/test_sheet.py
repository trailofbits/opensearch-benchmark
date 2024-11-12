import csv
import os
from dataclasses import dataclass
from pathlib import Path

import pytest
from googleapiclient.discovery import Resource, build

from report_gen.sheets import create_report
from report_gen.sheets.auth import authenticate


@dataclass
class SheetData:
    service: Resource
    spreadsheet_id: str


@pytest.fixture(scope="session")
def sheet_data() -> SheetData:
    """Authenticate sheets API and generate a spreadsheet.

    pytest fixture with session scope allows common setup to be used in multiple tests.
    """
    # Setup credentials
    credential_path_str = os.environ.get("GOOGLE_CRED")
    assert credential_path_str is not None, "Set GOOGLE_CRED to path to credentials.json to run tests"
    credential_path = Path(credential_path_str)
    token_path = Path("token.json")
    service = setup_api_access(credential_path, token_path)

    # Generate a report to check
    spreadsheet_id = create_report(
        benchmark_data=Path("test/data/test_data"),
        token_path=token_path,
        credential_path=None,  # token should be valid because we authenticated in setup_api_access
    )
    assert spreadsheet_id is not None, "Failed to create spreadsheet"

    return SheetData(service, spreadsheet_id)

    # TODO: Change above return to yeld and then delete spreadsheet_id. #noqa: TD002, TD003, FIX002
    # Requires new scope and google files API.


def setup_api_access(credential_path: Path, token_path: Path) -> Resource:
    creds = authenticate(credential_path, token_path)
    assert creds is not None, "Failed to authenticate Google API client"
    service = build("sheets", "v4", credentials=creds)
    assert service is not None, "Failed to initialize the API client"
    return service


def test_results_sheet(sheet_data: SheetData) -> None:
    """Check the results sheet.


    The results are put into a format that looks like:
    {
        # {Workload}-{Category}-{Operation}-{OS version}-{Es version}
        "nyc_taxis-Sorting-asc_sort_tip_amount-2.16.0-8.15.0": {
            'Workload': 'nyc_taxis',
            'Category': 'Sorting',
            ...
        }
    }
    The key is made of different columns used to identify unique rows.
    The value is a dict of header names and the corresponding cell value.
    This allows rows to be compared even if the layout of the columns changes in the future.
    """
    service = sheet_data.service
    spreadsheet_id = sheet_data.spreadsheet_id

    # Use these to identify rows that should be compared
    key_rows = ["Workload", "Category", "Operation", "OS version", "ES version"]

    def key(row: dict) -> str:
        return "-".join(row[header] for header in key_rows)

    actual = {key(row): row for row in read_result_sheet(service, spreadsheet_id)}

    with Path("test/data/results.csv").open() as f:
        reader = csv.DictReader(f)
        expected = {key(row): row for row in reader}

    actual_keys = set(actual.keys())
    expected_keys = set(expected.keys())

    if actual_keys != expected_keys:
        msg = "Columns do not match between actual and expected."
        msg += f"\nMissing columns: {expected_keys - actual_keys}"
        msg += f"\nExtra columns: {actual_keys - expected_keys}"
        raise AssertionError(msg)

    for key, expected_row in expected.items():
        actual_row = actual[key]
        assert expected_row == actual_row


def read_result_sheet(service: Resource, spreadsheet_id: str) -> list[dict]:
    result = (
        service.spreadsheets()
        .values()
        .get(
            spreadsheetId=spreadsheet_id,
            range="Results!A1:T",
        )
        .execute()
    )
    values = result.get("values", [])
    headers = values[0]
    return [dict(zip(headers, row, strict=False)) for row in values[1:]]


def test_summary_sheet(sheet_data: SheetData) -> None:
    """Check the summary sheet.

    Note, because this sheet holds tables, it just checks the raw CSV.
    Any changes to the structure will cause the test to fail.
    """
    service = sheet_data.service
    spreadsheet_id = sheet_data.spreadsheet_id

    result = (
        service.spreadsheets()
        .values()
        .get(
            spreadsheetId=spreadsheet_id,
            range="Summary!A1:L",
        )
        .execute()
    )
    actual = result.get("values", [])

    with Path("test/data/summary.csv").open() as f:
        reader = csv.reader(f)
        expected = list(reader)

    assert len(expected) == len(actual), f"Expected {len(expected)} rows, got {len(actual)}"

    # Sheets is weird about blank columns. If the columns mismatch try padding the one with fewer columns.
    if len(expected[0]) != len(actual[0]):
        max_len = max(len(expected[0]), len(actual[0]))
        expected = [row + [""] * (max_len - len(row)) for row in expected]
        actual = [row + [""] * (max_len - len(row)) for row in actual]
    assert len(expected[0]) == len(actual[0]), f"Expected {len(expected[0])} columns, got {len(actual[0])}"

    if actual != expected:
        # Attempt helpful error
        def sheet_col(index: int) -> str:
            """helper to convert x index to sheets letter"""
            return chr(ord("A") + index)

        msg = ""
        row_count = len(actual)
        col_count = len(actual[0])
        for y in range(row_count):
            for x in range(col_count):
                if actual[y][x] != expected[y][x]:
                    msg += f"{sheet_col(x)}{y} - Expected {expected[y][x]}, got {actual[y][x]}\n"
        raise AssertionError(msg)
