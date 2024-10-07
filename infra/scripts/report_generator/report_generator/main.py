import argparse
from argparse import ArgumentParser, Namespace

from os import walk
import os.path

import csv
from datetime import date
from pathlib import Path
from typing import Optional
from dataclasses import dataclass

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build, Resource
from googleapiclient.errors import HttpError

from . import __version__


SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


# Argument parser
def get_program_arguments() -> Namespace:
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


# Contains a single benchmark scenario, comparing OS to ES
@dataclass
class BenchmarkScenario:
    # The path to the directory containing the csv files
    base_path: Path

    # The benchmark name. The report generator will then access the files
    # named `os-<name>.csv` and `es-<name>.csv`
    name: str

    # The list of operations found in the csv files. If there are
    # differences between the two files, the benchmark scenario
    # is skipped
    operation_list: list[str]


# Enumerates the operations listed in the given csv file
def get_benchmark_data_operation_list(file_path: Path) -> list[str]:
    # Import the data in the sheet we just created
    row_list: list[list[str]]
    with open(file_path, "r") as csv_file:
        csv_reader = csv.reader(csv_file)
        row_list = list(csv_reader)

    # List all the unique operations we have in the benchmark data
    operation_list: list[str] = []

    for index, row in enumerate(row_list):
        if index == 0:
            continue

        operation: str = row[3]
        if len(operation) == 0:
            continue

        if not operation in operation_list:
            operation_list.append(operation)

    operation_list.sort()
    return operation_list


# Enumerates the .csv files in the given folder, looking for suitable benchmark
# scenarios.
#
# More specifically, the function will look for pairs of csv files named
# `os-<any_name>.csv` / `es-<any_name>.csv` with matching sets of operations
def get_benchmark_scenarios(folder_path: Path) -> Optional[list[BenchmarkScenario]]:
    benchmark_scenario_list: list[BenchmarkScenario] = []

    for directory_path, folder_name_list, file_name_list in walk(folder_path):
        for os_benchmark_data_file_name in file_name_list:
            if not os_benchmark_data_file_name.startswith("os-"):
                continue

            file_name_parts: str = os.path.splitext(os_benchmark_data_file_name)
            if len(file_name_parts) != 2 or file_name_parts[1] != ".csv":
                continue

            benchmark_name: str = file_name_parts[0][3:]

            os_benchmark_data_file_path: Path = Path(directory_path).joinpath(
                os_benchmark_data_file_name
            )

            es_benchmark_data_file_path: Path = Path(directory_path).joinpath(
                "es-" + benchmark_name + ".csv"
            )

            if not os.path.isfile(es_benchmark_data_file_path):
                print(
                    f"Skipping benchmark '{benchmark_name}' because the ES-specific data could not be found"
                )
                continue

            os_operation_list: Optional[list[str]] = get_benchmark_data_operation_list(
                os_benchmark_data_file_path
            )

            es_operation_list: Optional[list[str]] = get_benchmark_data_operation_list(
                es_benchmark_data_file_path
            )

            if set(os_operation_list) != set(es_operation_list):
                print(
                    f"Skipping benchmark '{benchmark_name}' because there's a mismatch in operation list between the ES and OS benchmark data"
                )
                continue

            benchmark_scenario: BenchmarkScenario = BenchmarkScenario(
                Path(directory_path), benchmark_name, os_operation_list
            )

            benchmark_scenario_list.append(benchmark_scenario)

        break

    if len(benchmark_scenario_list) == 0:
        return None

    return benchmark_scenario_list


# Authenticates a new session, using a credentials file. Creates a new token
# file at the given path
def authenticate_from_credentials(credentials_file_path: Path, token_file_path: Path):
    flow: InstalledAppFlow = InstalledAppFlow.from_client_secrets_file(
        credentials_file_path, SCOPES
    )
    creds: Credentials = flow.run_local_server(port=0)

    with open(token_file_path, "w") as token:
        token.write(creds.to_json())


# Restores a previously authenticated session, using a token file
def authenticate_from_token(token_file_path) -> Optional[Credentials]:
    creds: Credentials = None

    if not os.path.exists(token_file_path):
        print("Missing token file")
        return None

    creds = Credentials.from_authorized_user_file(token_file_path, SCOPES)
    if not creds or not creds.valid:
        print("Authentication has failed")
        return None

    return creds


# Creates a new spreadsheet, made of only the results sheet and its basic columns
def create_spreadsheet(service: Resource, title: str) -> Optional[str]:
    # Create a blank spreadsheet
    request_properties: dict = {
        "properties": {
            "title": title,
        },
        "sheets": [
            {"properties": {"title": "Results"}},
        ],
    }

    spreadsheet = (
        service.spreadsheets()
        .create(body=request_properties, fields="spreadsheetId")
        .execute()
    )

    spreadsheet_id: str = spreadsheet.get("spreadsheetId")

    # Add the column titles
    request_properties: dict = {
        "majorDimension": "ROWS",
        "values": [
            [
                "Sheet Name",
                "Clients",
                "Operation",
                "STDEV 50",
                "STDEV 90",
                "Average 50",
                "Average 90",
                "RSD 50",
                "RSD 90",
                "",
                "Sheet Name",
                "Clients",
                "Operation",
                "STDEV 50",
                "STDEV 90",
                "Average 50",
                "Average 90",
                "RSD 50",
                "RSD 90",
                "",
                "Comparison OS/ES",
            ],
        ],
    }

    service.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range="Results!A1",
        valueInputOption="USER_ENTERED",
        body=request_properties,
    ).execute()

    return spreadsheet_id


# Adjusts the columns in the given sheet according to their contents
def adjust_sheet_columns(service: Resource, spreadsheet_id: str, sheet_name: str):
    spreadsheet_properties: dict = (
        service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    )

    sheet_id: Optional[int] = None
    for sheet in spreadsheet_properties.get("sheets", ""):
        if sheet["properties"]["title"] == sheet_name:
            sheet_id = sheet["properties"]["sheetId"]
            break

    if sheet_id is None:
        print(f"Failed to locate the sheet named '{sheet_name}'. Formatting has failed")
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

    response: dict = (
        service.spreadsheets()
        .batchUpdate(spreadsheetId=spreadsheet_id, body={"requests": requests})
        .execute()
    )


# Imports a benchmark scenario into the given spreadsheet as a new sheet, while also
# updating the results data
def import_benchmark_scenario(
    service: Resource,
    spreadsheet_id: str,
    benchmark_scenario: BenchmarkScenario,
    starting_row_index: int,
) -> bool:
    for product_identifier in ["os", "es"]:
        # Load the rows from the benchmark data
        csv_path: Path = benchmark_scenario.base_path.joinpath(
            product_identifier + "-" + benchmark_scenario.name + ".csv"
        )

        row_list: list[list[str]]
        with open(csv_path, "r") as csv_file:
            csv_reader = csv.reader(csv_file)
            row_list = list(csv_reader)

        # Create a new sheet for this product
        sheet_name: str = f"{product_identifier}-{benchmark_scenario.name}"
        request_properties: dict = {
            "requests": [{"addSheet": {"properties": {"title": sheet_name}}}]
        }

        response: dict = (
            service.spreadsheets()
            .batchUpdate(spreadsheetId=spreadsheet_id, body=request_properties)
            .execute()
        )

        # Import the data in the sheet we just created
        row_list: list[list[str]]
        with open(csv_path, "r") as csv_file:
            csv_reader = csv.reader(csv_file)
            row_list = list(csv_reader)

        request_properties: dict = {
            "majorDimension": "ROWS",
            "values": row_list,
        }

        service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=f"{sheet_name}!A1",
            valueInputOption="USER_ENTERED",
            body=request_properties,
        ).execute()

        # Add the benchmark data to the Results sheet
        sheet_and_operation_rows: list[str] = []
        current_row: int = starting_row_index

        for operation in benchmark_scenario.operation_list:
            row_list: list[str] = [
                sheet_name,
                "",
                operation,
            ]

            column1: str
            column2: str
            if product_identifier == "os":
                column1 = "A"
                column2 = "C"
            else:
                column1 = "K"
                column2 = "M"

            row_list = row_list + [
                f'=STDEV.S(FILTER(INDIRECT({column1}{current_row}&"!F2:F"),INDIRECT({column1}{current_row}&"!B2:B")<>0,INDIRECT({column1}{current_row}&"!D2:D")={column2}{current_row},INDIRECT({column1}{current_row}&"!E2:E")="service_time"))',
                f'=STDEV.S(FILTER(INDIRECT({column1}{current_row}&"!G2:G"),INDIRECT({column1}{current_row}&"!B2:B")<>0,INDIRECT({column1}{current_row}&"!D2:D")={column2}{current_row},INDIRECT({column1}{current_row}&"!E2:E")="service_time"))',
                f'=AVERAGE(FILTER(INDIRECT({column1}{current_row}&"!F2:F"),INDIRECT({column1}{current_row}&"!B2:B")<>0,INDIRECT({column1}{current_row}&"!D2:D")={column2}{current_row},INDIRECT({column1}{current_row}&"!E2:E")="service_time"))',
                f'=AVERAGE(FILTER(INDIRECT({column1}{current_row}&"!G2:G"),INDIRECT({column1}{current_row}&"!B2:B")<>0,INDIRECT({column1}{current_row}&"!D2:D")={column2}{current_row},INDIRECT({column1}{current_row}&"!E2:E")="service_time"))',
            ]

            if product_identifier == "os":
                row_list = row_list + [
                    f"=D{current_row}/F{current_row}",
                    f"=E{current_row}/G{current_row}",
                ]
            else:
                row_list = row_list + [
                    f"=N{current_row}/P{current_row}",
                    f"=O{current_row}/Q{current_row}",
                ]

            sheet_and_operation_rows.append(row_list)
            current_row += 1

        request_properties: dict = {
            "majorDimension": "ROWS",
            "values": sheet_and_operation_rows,
        }

        insert_range: str
        if product_identifier == "os":
            insert_range = f"Results!A{starting_row_index}"
        else:
            insert_range = f"Results!K{starting_row_index}"

        service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=insert_range,
            valueInputOption="USER_ENTERED",
            body=request_properties,
        ).execute()

    # Add the comparison column
    comparison_rows: list[str] = []
    current_row = starting_row_index

    for operation in benchmark_scenario.operation_list:
        comparison_rows.append([f"=(Q{current_row}-G{current_row})/Q{current_row}"])
        current_row += 1

    request_properties: dict = {
        "majorDimension": "ROWS",
        "values": comparison_rows,
    }

    service.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range=f"Results!U{starting_row_index}",
        valueInputOption="USER_ENTERED",
        body=request_properties,
    ).execute()

    adjust_sheet_columns(service, spreadsheet_id, sheet_name)
    return True


# Creates a new report based on the benchmark data located at the given path
def create_report(creds: Credentials, benchmark_data: Path) -> Optional[str]:
    # Make sure we have data to process first
    benchmark_scenario_list: Optional[list[BenchmarkScenario]] = (
        get_benchmark_scenarios(benchmark_data)
    )

    if benchmark_scenario_list is None:
        print("No benchmark scenario found! Make sure that the file names are correct")
        return None

    # Initialize the api client
    service: Resource = build("sheets", "v4", credentials=creds)
    if service is None:
        print("Failed to initialize the API client")
        return None

    # Create a new spreadsheet
    current_date: str = date.today().strftime("%y-%m-%d")
    spreadsheet_id: Optional[str] = create_spreadsheet(
        service, f"{current_date} Benchmark Results"
    )

    if spreadsheet_id is None:
        print("Failed to create a new spreadsheet for the report")
        return None

    # Go through each benchmark scenario
    print("Processing the benchmark scenarios")
    current_base_row_index: int = 2

    for benchmark_scenario in benchmark_scenario_list:
        print(f" > {benchmark_scenario.name}")
        if not import_benchmark_scenario(
            service, spreadsheet_id, benchmark_scenario, current_base_row_index
        ):
            print("Failed to process the benchmark scenario")

        current_base_row_index += len(benchmark_scenario.operation_list) + 1

    adjust_sheet_columns(service, spreadsheet_id, "Results")
    return f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}"


def main() -> int:
    args: Namespace = get_program_arguments()
    if args.credentials is not None:
        authenticate_from_credentials(args.credentials, args.token)

    creds: Credentials = authenticate_from_token(args.token)
    if creds is None:
        return 1

    report_url: Optional[str] = create_report(creds, args.benchmark_data)
    if report_url is None:
        return 1

    print(f"Report URL: {report_url}")
    return 0


if __name__ == "__main__":
    main()
