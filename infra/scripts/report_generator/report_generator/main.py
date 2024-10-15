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

    spreadsheet: dict = (
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
                "Run Group",
                "Params",
                "Procedure",
                "Operation",
                "Category",
                "STDEV 50",
                "STDEV 90",
                "Average 50",
                "Average 90",
                "RSD 50",
                "RSD 90",
                "",
                "Sheet Name",
                "Run Group",
                "Params",
                "Procedure",
                "Operation",
                "Category",
                "STDEV 50",
                "STDEV 90",
                "Average 50",
                "Average 90",
                "RSD 50",
                "RSD 90",
                "",
                "Comparison\n|ES-OS| / AVG(ES,OS)",
                "Comparison\nES/OS",
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

    return spreadsheet_id


# Adds a 'categories' sheet
def add_categories_sheet(service: Resource, spreadsheet_id: str):
    request_properties: dict = {
        "requests": [{"addSheet": {"properties": {"title": "Categories"}}}]
    }

    response: dict = (
        service.spreadsheets()
        .batchUpdate(spreadsheetId=spreadsheet_id, body=request_properties)
        .execute()
    )

    spec_list: dict = [
        {
            "workload": "big5",
            "categories": {
                "Sorting": [
                    "asc_sort_timestamp",
                    "asc_sort_timestamp_can_match_shortcut",
                    "asc_sort_timestamp_no_can_match_shortcut",
                    "asc_sort_with_after_timestamp",
                    "desc_sort_timestamp",
                    "desc_sort_timestamp_can_match_shortcut",
                    "desc_sort_timestamp_no_can_match_shortcut",
                    "sort_keyword_can_match_shortcut",
                    "desc_sort_with_after_timestamp",
                    "sort_keyword_no_can_match_shortcut",
                    "sort_numeric_asc",
                    "sort_numeric_asc_with_match",
                    "sort_numeric_desc",
                    "sort_numeric_desc_with_match",
                ],
                "Team Aggregations": [
                    "cardinality-agg-high",
                    "cardinality-agg-low",
                    "composite_terms-keyword",
                    "composite-terms",
                    "keyword-terms",
                    "keyword-terms-low-cardinality",
                    "multi_terms-keyword",
                ],
                "Date Histogram": [
                    "composite-date_histogram-daily",
                    "date_histogram_hourly_agg",
                    "date_histogram_minute_agg",
                    "range-auto-date-histo",
                    "range-auto-date-histo-with-metrics",
                ],
                "General Operations": [
                    "scroll",
                    "default",
                ],
                "Text Querying": [
                    "query-string-on-message",
                    "query-string-on-message-filtered",
                    "query-string-on-message-filtered-sorted-num",
                    "term",
                ],
                "Range Queries": [
                    "range",
                    "keyword-in-range",
                    "range_field_conjunction_big_range_big_term_query",
                    "range_field_conjunction_small_range_big_term_query",
                    "range_field_conjunction_small_range_small_term_query",
                    "range_field_disjunction_big_range_small_term_query",
                    "range-agg-1",
                    "range-agg-2",
                    "range-numeric",
                ],
            },
        },
        {
            "workload": "noaa",
            "categories": {
                "Date Histogram": [
                    "date-histo-entire-range",
                    "date-histo-geohash-grid",
                    "date-histo-geotile-grid",
                    "date-histo-histo",
                    "date-histo-numeric-terms",
                    "date-histo-string-significant-terms-via-default-strategy",
                    "date-histo-string-significant-terms-via-global-ords",
                    "date-histo-string-significant-terms-via-map",
                    "date-histo-string-terms-via-default-strategy",
                    "date-histo-string-terms-via-global-ords",
                    "date-histo-string-terms-via-map",
                    "range-auto-date-histo",
                    "range-auto-date-histo-with-metrics",
                    "range-auto-date-histo-with-time-zone",
                ],
                "Team Aggregations": [
                    "keyword-terms",
                    "keyword-terms-low-cardinality",
                    "keyword-terms-low-cardinality-min",
                    "keyword-terms-min",
                    "keyword-terms-numeric-terms",
                    "numeric-terms-numeric-terms",
                ],
                "Range Queries": [
                    "range-aggregation",
                    "range-date-histo",
                    "range-date-histo-with-metrics",
                    "range-numeric-significant-terms",
                ],
            },
        },
        {
            "workload": "nyc_taxis",
            "categories": {
                "Aggregation": [
                    "distance_amount_agg",
                    "date_histogram_agg",
                    "autohisto_agg",
                ],
                "Other": [
                    "range",
                    "default",
                ],
                "Sorting": [
                    "desc_sort_tip_amount",
                    "asc_sort_tip_amount",
                ],
            },
        },
        {
            "workload": "pmc",
            "categories": {
                "Other": [
                    "default",
                ],
                "Text Querying": [
                    "term",
                    "phrase",
                ],
                "Aggregation": [
                    "articles_monthly_agg_uncached",
                    "articles_monthly_agg_uncached",
                ],
                "Other": [
                    "scroll",
                ],
            },
        },
    ]

    # Generate the rows in the spreadsheet
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

        # Get the name of the workload
        workload_column_index: Optional[int] = None

        for header_column_index, header_column in enumerate(row_list[0]):
            if header_column == "workload":
                workload_column_index = header_column_index
                break

        if workload_column_index is None:
            raise ValueError(
                "Failed to extract the workload name from the benchmark data"
            )

        workload_name: str = row_list[1][workload_column_index]

        # Create a new sheet for this product+workload
        sheet_name: str = f"{product_identifier}-{benchmark_scenario.name}"
        request_properties: dict = {
            "requests": [{"addSheet": {"properties": {"title": sheet_name}}}]
        }

        response: dict = (
            service.spreadsheets()
            .batchUpdate(spreadsheetId=spreadsheet_id, body=request_properties)
            .execute()
        )

        # Load the benchmark data from file
        row_list: list[list[str]]
        with open(csv_path, "r") as csv_file:
            csv_reader = csv.reader(csv_file)
            row_list = list(csv_reader)

        input_columns: dict[str, int] = {}
        for index, header_column in enumerate(row_list[0]):
            input_columns[header_column] = index

        # When changing this, make sure to update the formulas
        output_column_order: list[str] = [
            "environment",
            "user-tags\\.run",
            "workload",
            "operation",
            "name",
            "value\\.50_0",
            "value\\.90_0",
            "user-tags\\.run-group",
            "test-procedure",
            "workload\\.index_merge_policy",
            "workload\\.max_num_segments",
            "workload\\.bulk_indexing_clients",
            "workload\\.target_throughput",
            "workload\\.number_of_replicas",
            "distribution-version",
        ]

        processed_row_list: list[list[str]] = [output_column_order]

        for row_index, row in enumerate(row_list):
            if row_index == 0:
                continue

            processed_row: list[str] = []
            for column_name in output_column_order:
                source_column_index: int = input_columns[column_name]
                processed_row.append(row[source_column_index])

            processed_row_list.append(processed_row)

        # Import the data in the sheet we just created
        request_properties: dict = {
            "majorDimension": "ROWS",
            "values": processed_row_list,
        }

        service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=f"{sheet_name}!A1",
            valueInputOption="USER_ENTERED",
            body=request_properties,
        ).execute()

        # Determine what's the category range for this specific workload. Note that these indexes
        # are 1-based
        result: dict = (
            service.spreadsheets()
            .values()
            .get(spreadsheetId=spreadsheet_id, range="Categories!A:A")
            .execute()
        )

        category_range_start: Optional[int] = None
        category_range_end: Optional[int] = None

        category_sheet_row_list: list[list[str]] = result.get("values", [])
        for row_index, category_sheet_row in enumerate(category_sheet_row_list):
            if category_range_start is None:
                if category_sheet_row[0] == workload_name:
                    category_range_start = row_index + 1
                else:
                    continue

            if category_range_end is None:
                if category_sheet_row[0] != workload_name:
                    category_range_end = row_index
                    break

            if category_range_start is not None and category_range_end is not None:
                break

        if category_range_start is None or category_range_end is None:
            raise ValueError(
                f"Failed to determine the category range for the following workload and sheet: {sheet_name}, {workload_name}"
            )

        # Add the benchmark data to the Results sheet
        sheet_and_operation_rows: list[str] = []
        current_row: int = starting_row_index

        for operation in benchmark_scenario.operation_list:
            column1: str
            column2: str
            operation_column: str
            if product_identifier == "os":
                column1 = "A"
                column2 = "E"
                operation_column = "E"

            else:
                column1 = "N"
                column2 = "R"
                operation_column = "R"

            row_list: list[str] = [
                sheet_name,
                f'=INDIRECT({column1}{current_row}&"!H{current_row}")',
                f'=CONCATENATE("index_merge_policy=", INDIRECT({column1}{current_row}&"!J{current_row}"), ", max_num_segments=", INDIRECT({column1}{current_row}&"!K{current_row}"), ", bulk_indexing_clients=", INDIRECT({column1}{current_row}&"!L{current_row}"), ", target_throughput=", INDIRECT({column1}{current_row}&"!M{current_row}"), ", number_of_replicas=", INDIRECT({column1}{current_row}&"!N{current_row}"))',
                f'=INDIRECT({column1}{current_row}&"!I{current_row}")',
                operation,
                f"=VLOOKUP({operation_column}{current_row}, Categories!B${category_range_start}:C${category_range_end}, 2, FALSE)",
                f'=STDEV.S(FILTER(INDIRECT({column1}{current_row}&"!F2:F"),INDIRECT({column1}{current_row}&"!B2:B")<>0,INDIRECT({column1}{current_row}&"!D2:D")={column2}{current_row},INDIRECT({column1}{current_row}&"!E2:E")="service_time"))',
                f'=STDEV.S(FILTER(INDIRECT({column1}{current_row}&"!G2:G"),INDIRECT({column1}{current_row}&"!B2:B")<>0,INDIRECT({column1}{current_row}&"!D2:D")={column2}{current_row},INDIRECT({column1}{current_row}&"!E2:E")="service_time"))',
                f'=AVERAGE(FILTER(INDIRECT({column1}{current_row}&"!F2:F"),INDIRECT({column1}{current_row}&"!B2:B")<>0,INDIRECT({column1}{current_row}&"!D2:D")={column2}{current_row},INDIRECT({column1}{current_row}&"!E2:E")="service_time"))',
                f'=AVERAGE(FILTER(INDIRECT({column1}{current_row}&"!G2:G"),INDIRECT({column1}{current_row}&"!B2:B")<>0,INDIRECT({column1}{current_row}&"!D2:D")={column2}{current_row},INDIRECT({column1}{current_row}&"!E2:E")="service_time"))',
            ]

            if product_identifier == "os":
                row_list = row_list + [
                    f"=G{current_row}/I{current_row}",
                    f"=H{current_row}/J{current_row}",
                ]
            else:
                row_list = row_list + [
                    f"=T{current_row}/V{current_row}",
                    f"=U{current_row}/W{current_row}",
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
            insert_range = f"Results!N{starting_row_index}"

        service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=insert_range,
            valueInputOption="USER_ENTERED",
            body=request_properties,
        ).execute()

    adjust_sheet_columns(service, spreadsheet_id, sheet_name)

    # Add the comparison column
    comparison_rows: list[str] = []
    current_row = starting_row_index

    for operation in benchmark_scenario.operation_list:
        comparison_rows.append(
            [
                f"=ABS(J{current_row}-V{current_row})*IF(J{current_row}>V{current_row},-1,1)/((J{current_row}+V{current_row})/2)",
                f"=V{current_row}/J{current_row}",
            ]
        )

        current_row += 1

    request_properties: dict = {
        "majorDimension": "ROWS",
        "values": comparison_rows,
    }

    service.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range=f"Results!AA{starting_row_index}",
        valueInputOption="USER_ENTERED",
        body=request_properties,
    ).execute()

    adjust_sheet_columns(service, spreadsheet_id, sheet_name)
    return True


# Hides the specified columns in the given sheet
def hide_columns(
    service: Resource, spreadsheet_id: str, sheet_name: str, column_list: list[str]
):
    spreadsheet_properties: dict = (
        service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    )

    sheet_id: Optional[int] = None
    for sheet in spreadsheet_properties.get("sheets", ""):
        if sheet["properties"]["title"] == sheet_name:
            sheet_id = sheet["properties"]["sheetId"]
            break

    if sheet_id is None:
        print(
            f"Failed to locate the sheet named '{sheet_name}'. Failed to hide the columns"
        )
        return

    request_list: list[dict] = []
    for column in column_list:
        request_list.append(
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
        )

    body: dict = {"requests": request_list}
    service.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id, body=body
    ).execute()


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
    hide_columns(service, spreadsheet_id, "Results", ["C", "P"])

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
