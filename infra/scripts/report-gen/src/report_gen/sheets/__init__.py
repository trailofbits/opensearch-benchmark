"""Functions to create a summary report in Google Sheets."""

import logging
from datetime import date
from pathlib import Path
from typing import TYPE_CHECKING, cast

from googleapiclient.discovery import Resource, build

from .auth import authenticate_from_credentials, authenticate_from_token
from .common import get_category_operation_map
from .import_data import ImportData
from .result import Result
from .summary import Summary

if TYPE_CHECKING:
    from google.oauth2.credentials import Credentials


logger = logging.getLogger(__name__)


def create_report(benchmark_data: Path, token_path: Path, credential_path: Path | None) -> bool:
    """Create a spreadsheet report form the provided benchmark data."""
    # Authenticate credentials
    if credential_path is not None:
        authenticate_from_credentials(credential_path, token_path)
    creds: Credentials | None = authenticate_from_token(token_path)
    if creds is None:
        return False

    # Initialize the api client
    service: Resource = build("sheets", "v4", credentials=creds)
    if service is None:
        logger.error("Failed to initialize the API client")
        return False

    # Create a new spreadsheet
    current_date: str = date.today().strftime("%Y-%m-%d")  # noqa: DTZ011
    spreadsheet_id: str | None = _create_spreadsheet(service, f"{current_date} | Benchmark Results")
    if spreadsheet_id is None:
        logger.error("Error, spreadsheet not created.")
        return False

    # Import data to spreadsheet
    data = ImportData(service=service, spreadsheet_id=spreadsheet_id, folder=benchmark_data)
    if not data.get():
        logger.error("Error importing data")
        return False
    logger.info("Imported data successfully")

    # Create Results sheet
    result = Result(service=service, spreadsheet_id=spreadsheet_id)
    if not result.get():
        logger.error("Error creating results sheet")
        return False
    logger.info("Results processed successfully")

    # Create Summary sheet
    summary = Summary(service=service, spreadsheet_id=spreadsheet_id)
    if not summary.get():
        logger.error("Error creating summary sheet")
        return False
    logger.info("Summary processed successfully")

    # Output spreadsheet URL for ease
    report_url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}"
    logger.info(f"Report URL: {report_url}")

    return True


def _resize_sheet(service: Resource, spreadsheet_id: str, sheet_name: str, width: int, height: int) -> None:
    """Resize the given sheet."""
    spreadsheet_properties: dict = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()

    sheet_id: int | None = None
    for sheet in spreadsheet_properties.get("sheets", ""):
        if sheet["properties"]["title"] == sheet_name:
            sheet_id = sheet["properties"]["sheetId"]
            break

    if sheet_id is None:
        logger.error(f"Failed to locate the sheet named '{sheet_name}'. Formatting has failed")
        return

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
    _resize_sheet(service, spreadsheet_id, sheet_name, width, height)

    return spreadsheet_id


def _add_sheet(service: Resource, spreadsheet_id: str, sheet_name: str) -> None:
    request_properties: dict = {"requests": [{"addSheet": {"properties": {"title": sheet_name}}}]}

    service.spreadsheets().batchUpdate(spreadsheetId=spreadsheet_id, body=request_properties).execute()


def _create_spreadsheet(service: Resource, title: str) -> str | None:
    """Create a new spreadsheet with the initial columns."""
    # Create a new spreadsheet and add the initial columns
    spreadsheet_id: str | None = _create_blank_spreadsheet(service, title, "Summary", 50, 100)
    if spreadsheet_id is None:
        return None

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
                "OS: STDEV 50",
                "OS: STDEV 90",
                "OS: Average 50",
                "OS: Average 90",
                "OS: RSD 50",
                "OS: RSD 90",
                "",
                "ES version",
                "ES: STDEV 50",
                "ES: STDEV 90",
                "ES: Average 50",
                "ES: Average 90",
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
    _adjust_sheet_columns(service, spreadsheet_id, "Categories")

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


def _adjust_sheet_columns(service: Resource, spreadsheet_id: str, sheet_name: str) -> None:
    """Adjust the columns in the given sheet according to their contents."""
    spreadsheet_properties: dict = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()

    sheet_id: int | None = None
    for sheet in spreadsheet_properties.get("sheets", ""):
        if sheet["properties"]["title"] == sheet_name:
            sheet_id = sheet["properties"]["sheetId"]
            break

    if sheet_id is None:
        logger.error(f"Failed to locate the sheet named '{sheet_name}'. Formatting has failed")
        return

    sheet_properties: dict = sheet["properties"]
    column_count: int = sheet_properties.get("gridProperties", {}).get("columnCount", 0)

    requests: list[dict] = [
        {
            "autoResizeDimensions": {
                "dimensions": {
                    "sheetId": sheet_id,
                    "dimension": "COLUMNS",
                    "startIndex": 0,
                    "endIndex": column_count,
                }
            }
        }
    ]

    response: dict = (  # noqa: F841
        service.spreadsheets().batchUpdate(spreadsheetId=spreadsheet_id, body={"requests": requests}).execute()
    )


def _hide_columns(service: Resource, spreadsheet_id: str, sheet_name: str, column_list: list[str]) -> None:
    """Hide the specified columns in the given sheet."""
    spreadsheet_properties: dict = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()

    sheet_id: int | None = None
    for sheet in spreadsheet_properties.get("sheets", ""):
        if sheet["properties"]["title"] == sheet_name:
            sheet_id = sheet["properties"]["sheetId"]
            break

    if sheet_id is None:
        logger.error(f"Failed to locate the sheet named '{sheet_name}'. Failed to hide the columns")
        return

    request_list: list[dict] = []
    request_list = [
        {
            "updateDimensionProperties": {
                "range": {
                    "sheetId": sheet_id,
                    "dimension": "COLUMNS",
                    "startIndex": ord(column) - ord("A"),
                    "endIndex": ord(column) - ord("A") + 1,
                },
                "properties": {"hiddenByUser": True},
                "fields": "hiddenByUser",
            }
        }
        for column in column_list
    ]

    body: dict = {"requests": request_list}
    service.spreadsheets().batchUpdate(spreadsheetId=spreadsheet_id, body=body).execute()
