"""Functions to create a summary report in Google Sheets."""

import logging
import time
from datetime import date
from pathlib import Path
from typing import cast

from googleapiclient.discovery import Resource, build

from .auth import authenticate
from .common import adjust_sheet_columns, get_category_operation_map, get_sheet_id
from .import_data import ImportData
from .osversion import OSVersion
from .overall import OverallSheet
from .result import Result
from .summary import Summary

logger = logging.getLogger(__name__)


def create_report(benchmark_data: Path, token_path: Path, credential_path: Path | None) -> str | None:
    """Create a spreadsheet report form the provided benchmark data."""
    # Authenticate credentials
    creds = authenticate(credential_path, token_path)
    if creds is None:
        return None

    # Initialize the api client
    service: Resource = build("sheets", "v4", credentials=creds)
    if service is None:
        logger.error("Failed to initialize the API client")
        return None

    # Create a new spreadsheet
    current_date: str = date.today().strftime("%Y-%m-%d")  # noqa: DTZ011
    spreadsheet_id: str | None = _create_spreadsheet(service, f"{current_date} | Benchmark Results")
    if spreadsheet_id is None:
        logger.error("Error, spreadsheet not created.")
        return None

    # Import data to spreadsheet
    data = ImportData(service=service, spreadsheet_id=spreadsheet_id, folder=benchmark_data)
    if not data.get():
        logger.error("Error importing data")
        return None
    logger.info("Imported data successfully")

    # Create Results sheet
    result = Result(service=service, spreadsheet_id=spreadsheet_id)
    if not result.get():
        logger.error("Error creating results sheet")
        return None
    logger.info("Results processed successfully")

    # Create a pause here because of the default limit of 60 requests per minute
    logger.info("Pausing for 60 seconds because of Google API rate limiting.")
    time.sleep(60)

    # Create Summary sheet
    summary = Summary(service=service, spreadsheet_id=spreadsheet_id)
    if not summary.get():
        logger.error("Error creating summary sheet")
        return None
    logger.info("Summary processed successfully")

    # Create a pause here because of the default limit of 60 requests per minute
    logger.info("Pausing for 60 seconds because of Google API rate limiting.")
    time.sleep(60)

    # Create OS version sheets for big5
    os_version = OSVersion(service=service, spreadsheet_id=spreadsheet_id)
    if not os_version.get():
        logger.error("Error creating OS versions sheet")
        return None
    logger.info("OS versions processed successfully")

    # Create a pause here because of the default limit of 60 requests per minute
    logger.info("Pausing for 60 seconds because of Google API rate limiting.")
    time.sleep(60)

    # Create Overall sheet for big5
    overall_sheet = OverallSheet(service=service, spreadsheet_id=spreadsheet_id)
    if not overall_sheet.get():
        logger.error("Error creating Overall sheet")
        return None
    logger.info("Overall processed successfully")

    # Output spreadsheet URL for ease
    report_url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}"
    logger.info(f"Report URL: {report_url}")

    return spreadsheet_id


def _resize_sheet(service: Resource, spreadsheet_id: str, sheet_id: int, width: int, height: int) -> None:
    """Resize the given sheet."""
    body: dict = {
        "requests": [
            {
                "updateSheetProperties": {
                    "properties": {
                        "sheetId": sheet_id,
                        "gridProperties": {"rowCount": height, "columnCount": width},
                    },
                    "fields": "gridProperties(rowCount,columnCount)",
                }
            }
        ]
    }

    service.spreadsheets().batchUpdate(spreadsheetId=spreadsheet_id, body=body).execute()


def _create_blank_spreadsheet(service: Resource, title: str, sheet_name: str, width: int, height: int) -> str | None:
    """Create a new spreadsheet with a single sheet."""
    request_properties: dict = {
        "properties": {
            "title": title,
        },
        "sheets": [
            {"properties": {"title": sheet_name}},
        ],
    }

    spreadsheet: dict = service.spreadsheets().create(body=request_properties, fields="spreadsheetId").execute()

    spreadsheet_id: str = cast(str, spreadsheet.get("spreadsheetId"))
    sheet_id, _ = get_sheet_id(service, spreadsheet_id, sheet_name)
    if sheet_id is None:
        logger.error(f"Failed to locate the sheet named '{sheet_name}'. Formatting has failed")
        return None
    _resize_sheet(service, spreadsheet_id, sheet_id, width, height)

    return spreadsheet_id


def _add_sheet(service: Resource, spreadsheet_id: str, sheet_name: str) -> None:
    request_properties: dict = {"requests": [{"addSheet": {"properties": {"title": sheet_name}}}]}

    service.spreadsheets().batchUpdate(spreadsheetId=spreadsheet_id, body=request_properties).execute()


def _create_spreadsheet(service: Resource, title: str) -> str | None:
    """Create a new spreadsheet with the initial columns."""
    # Create Overall Spread sheet for big5
    spreadsheet_id: str | None = _create_blank_spreadsheet(service, title, "Overall Spread", 50, 500)
    if spreadsheet_id is None:
        return None

    # Create sheets for OS versions 2.16, 2.17, and 2.18
    for name in ["OS 2.17.1", "OS 2.18.0", "OS 2.19.1"]:
        _add_sheet(service, spreadsheet_id, name)

    # Create a new spreadsheet and add the initial columns
    _add_sheet(service, spreadsheet_id, "Summary")

    # Create a new sheet for aggregated results
    _add_sheet(service, spreadsheet_id, "Results")

    request_properties: dict = {
        "majorDimension": "ROWS",
        "values": [
            [
                "Workload",
                "Category",
                "Operation",
                "Comparison\nES/OS",
                "",
                "OS version",
                "OS SubType",
                "OS: STDEV 50",
                "OS: STDEV 90",
                "OS: Median 50",
                "OS: Median 90",
                "OS: RSD 50",
                "OS: RSD 90",
                "",
                "ES version",
                "ES SubType",
                "ES: STDEV 50",
                "ES: STDEV 90",
                "ES: Median 50",
                "ES: Median 90",
                "ES: RSD 50",
                "ES: RSD 90",
            ],
        ],
    }

    service.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range="Results!A1",
        valueInputOption="USER_ENTERED",
        body=request_properties,
    ).execute()

    # Add the categories now so that we can query the row count when generating the
    # VLOOKUP formula for the category column
    _add_categories_sheet(service, spreadsheet_id)
    sheet_id, sheet = get_sheet_id(service, spreadsheet_id, "Categories")
    if sheet_id is None:
        logger.error("Failed to locate the sheet named 'Categories'. Formatting has failed")
        return None
    adjust_sheet_columns(service, spreadsheet_id, sheet_id, sheet)

    # Create a new sheet for all benchmark data
    _add_sheet(service, spreadsheet_id, "raw")

    return spreadsheet_id


def _add_categories_sheet(service: Resource, spreadsheet_id: str) -> None:
    """Add a 'categories' sheet to the spreadsheet."""
    _add_sheet(service, spreadsheet_id, "Categories")

    # Generate the rows in the spreadsheet
    spec_list: list[dict] = get_category_operation_map()
    row_list: list[list[str]] = [["Workload", "Operation", "Category"]]

    for spec in spec_list:
        workload_name: str = spec["workload"]

        for category_name in spec["categories"]:
            for operation_name in spec["categories"][category_name]:
                row_list.append([workload_name, operation_name, category_name])  # noqa: PERF401

    request_properties: dict = {
        "majorDimension": "ROWS",
        "values": row_list,
    }

    service.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range="Categories!A1",
        valueInputOption="USER_ENTERED",
        body=request_properties,
    ).execute()
