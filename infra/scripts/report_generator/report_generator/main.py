import argparse
from argparse import ArgumentParser, Namespace

from os import walk
import os.path

from datetime import date
from pathlib import Path
from typing import Optional, Tuple, Any

from report_generator.common import get_category_operation_map, get_sheet_id, adjust_sheet_columns
from report_generator.import_data import ImportData
from report_generator.result import Result
from report_generator.summary import Summary

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build, Resource
from googleapiclient.errors import HttpError

from . import __version__


# Limit access to files created by this app
# See: https://developers.google.com/identity/protocols/oauth2/scopes#sheets
SCOPES = ["https://www.googleapis.com/auth/drive.file"]


def get_program_arguments() -> Namespace:
    """Parses the program arguments"""

    parser: ArgumentParser = ArgumentParser(
        description="opensearch benchmark report generator"
    )

    def directory_path_parser(user_input: str) -> Path:
        if os.path.isdir(user_input):
            return Path(user_input)
        else:
            raise argparse.ArgumentTypeError(f"Not a valid folder path: {user_input}")

    def existing_file_path_parser(user_input: str) -> Path:
        if os.path.isfile(user_input):
            return Path(user_input)
        else:
            raise argparse.ArgumentTypeError(f"Not an existing file path: {user_input}")

    parser.add_argument(
        "--credentials",
        help="Path to the credentials file",
        type=existing_file_path_parser,
        default=None,
    )

    parser.add_argument(
        "--token",
        help="Path to the token file. If it's missing, use in combination with the --credentials parameter",
        required=True,
    )

    parser.add_argument(
        "--benchmark-data",
        help="Path to the benchmark data folder, which should contain the raw .csv files",
        required=True,
        type=directory_path_parser,
    )

    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )

    return parser.parse_args()


def authenticate_from_credentials(credentials_file_path: Path, token_file_path: Path):
    """Authenticates a new session, using a credentials file. Creates a new token file at the given path"""

    flow: InstalledAppFlow = InstalledAppFlow.from_client_secrets_file(
        credentials_file_path, SCOPES
    )
    creds: Credentials = flow.run_local_server(port=0)

    with open(token_file_path, "w") as token:
        token.write(creds.to_json())


def authenticate_from_token(token_file_path) -> Optional[Credentials]:
    """Restores a previously authenticated session, using a token file"""

    creds: Credentials = None

    if not os.path.exists(token_file_path):
        print("Missing token file")
        return None

    creds = Credentials.from_authorized_user_file(token_file_path, SCOPES)
    if not creds or not creds.valid:
        print("Authentication has failed")
        return None

    return creds


def resize_sheet(
    service: Resource, spreadsheet_id: str, sheet_name: str, width: int, height: int
):
    """Resizes the given sheet"""

    sheet_id = get_sheet_id(service, spreadsheet_id, sheet_name)
    if sheet_id is None:
        print(f"Failed to locate the sheet named '{sheet_name}'. Formatting has failed")
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

    service.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id, body=body
    ).execute()


def create_blank_spreadsheet(
    service: Resource, title: str, sheet_name: str, width: int, height: int
) -> Optional[str]:
    """Creates a new spreadsheet with a single sheet"""

    request_properties: dict = {
        "properties": {
            "title": title,
        },
        "sheets": [
            {"properties": {"title": sheet_name}},
        ],
    }

    spreadsheet: dict = (
        service.spreadsheets()
        .create(body=request_properties, fields="spreadsheetId")
        .execute()
    )

    spreadsheet_id: str = spreadsheet.get("spreadsheetId")
    resize_sheet(service, spreadsheet_id, sheet_name, width, height)

    return spreadsheet_id


def create_spreadsheet(service: Resource, title: str) -> Optional[str]:
    """Creates a new spreadsheet with the initial columns"""

    # Create a new spreadsheet and add the initial columns
    spreadsheet_id: str = create_blank_spreadsheet(service, title, "Summary", 500, 1000)

    # Create a new sheet for aggregated results
    sheet_name: str = "Results"
    request_properties: dict = {
        "requests": [{"addSheet": {"properties": {"title": sheet_name}}}]
    }
    response: dict = (
        service.spreadsheets()
        .batchUpdate(spreadsheetId=spreadsheet_id, body=request_properties)
        .execute()
    )

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
    add_categories_sheet(service, spreadsheet_id)
    adjust_sheet_columns(service, spreadsheet_id, "Categories")

    # Create a new sheet for all benchmark data
    sheet_name: str = "raw"
    request_properties: dict = {
        "requests": [{"addSheet": {"properties": {"title": sheet_name}}}]
    }
    response: dict = (
        service.spreadsheets()
        .batchUpdate(spreadsheetId=spreadsheet_id, body=request_properties)
        .execute()
    )

    return spreadsheet_id


def add_categories_sheet(service: Resource, spreadsheet_id: str):
    """Adds a 'categories' sheet to the spreadsheet"""

    request_properties: dict = {
        "requests": [{"addSheet": {"properties": {"title": "Categories"}}}]
    }

    service.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id, body=request_properties
    ).execute()

    # Generate the rows in the spreadsheet
    spec_list: list[dict] = get_category_operation_map()
    row_list: list[list[str]] = [["Workload", "Operation", "Category"]]

    for spec in spec_list:
        workload_name: str = spec["workload"]

        for category_name in spec["categories"].keys():
            for operation_name in spec["categories"][category_name]:
                row_list.append([workload_name, operation_name, category_name])

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


def init_spreadsheet(
    creds: Credentials
) -> Tuple[Any|None,str|None]:
    """Creates a new spreadsheet and returns the service and spreadsheet id"""

    # Initialize the api client
    service: Resource = build("sheets", "v4", credentials=creds)
    if service is None:
        print("Failed to initialize the API client")
        return None,None

    # Create a new spreadsheet
    current_date: str = date.today().strftime("%Y-%m-%d")
    spreadsheet_id: Optional[str] = create_spreadsheet(
        service, f"{current_date} | Benchmark Results"
    )
    if spreadsheet_id is not None:
        return service, spreadsheet_id
    return None,None


def main() -> bool:
    """Main entry point"""

    # Get arguments
    args: Namespace = get_program_arguments()

    # Authenticate credentials
    if args.credentials is not None:
        authenticate_from_credentials(args.credentials, args.token)
    creds: Credentials = authenticate_from_token(args.token)
    if creds is None:
        return False

    # Initialize spreadsheet
    service, spreadsheet_id = init_spreadsheet(creds)
    if service is None or spreadsheet_id is None:
        print("Error, spreadsheet not created.")
        return False

    # Import data to spreadsheet
    data = ImportData(
        service=service,
        spreadsheet_id=spreadsheet_id,
        folder=args.benchmark_data
    )
    if not data.get():
        print("Error importing data")
        return False
    print("Imported data successfully")

    # Create Results sheet
    result = Result(
        service=service,
        spreadsheet_id=spreadsheet_id
    )
    if not result.get():
        print("Error creating results sheet")
        return False
    print("Results processed successfully")

    # Create Summary sheet
    summary = Summary(
        service=service,
        spreadsheet_id=spreadsheet_id
    )
    if not summary.get():
        print("Error creating summary sheet")
        return False
    print("Summary processed successfully")

    # Output spreadsheet URL for ease
    report_url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}"
    print(f"Report URL: {report_url}")

    return True