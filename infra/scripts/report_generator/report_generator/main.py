import argparse
from argparse import ArgumentParser, Namespace

from os import walk
import os.path

from datetime import date
from pathlib import Path
from typing import Optional, Tuple, Any

from report_generator.import_data import ImportData
from report_generator.common import get_category_operation_map

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


# Enumerates the operations listed in the given csv file
def get_benchmark_data_operation_list(file_path: Path) -> set[str]:
    # Read the data in the sheet we just created
    row_list: list[list[str]]
    with open(file_path, "r") as csv_file:
        csv_reader = csv.reader(csv_file)
        row_list = list(csv_reader)

    # Find the 'operation' column
    if len(row_list) < 1:
        raise ValueError(
            f"The following .csv file does not have a header row: {file_path}"
        )

    header_row: list[str] = row_list[0]
    operation_column: Optional[int] = None

    for index, column in enumerate(header_row):
        if column == "operation":
            operation_column = index
            break

    if operation_column is None:
        raise ValueError(
            f"The following .csv file does not have an operation column: {file_path}"
        )

    # List all the unique operations we have in the benchmark data
    operation_set: set[str] = set()

    for index, row in enumerate(row_list):
        if index == 0:
            continue

        operation: str = row[operation_column]
        if len(operation) == 0:
            continue

        operation_set.add(operation)

    return operation_set


# Enumerates the .csv files in the given folder, looking for suitable benchmark
# scenarios.
def discover_benchmark_scenarios(
    folder_path: Path
) -> list[Path] | None:
    benchmark_scenario_list: list[Path] = []

    spec_list: list[dict] = get_category_operation_map()
    op_dict: dict[str,set[str]] = {}
    for d in spec_list:
        workload = d["workload"]
        op_dict[workload] = set()
        for category, operation_list in d["categories"].items():
            for operation in operation_list:
                op_dict[workload].add(operation)

    csv_file: list[Path] = []
    for directory_path, folder_name_list, file_name_list in walk(folder_path):
        for file_name in file_name_list:
            if not file_name.endswith(".csv"):
                continue

            csv_file.append(Path(directory_path).joinpath(file_name))

    for path in csv_file:
        op_set: set[str] = get_benchmark_data_operation_list(path)

        workload = path.name.split('-')[5]

        # Determine if this benchmark contains all operations expected
        if op_set != op_dict[workload]:
            continue
        benchmark_scenario_list.append(path)

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


# Resizes the given spreadsheet
def resize_sheet(
    service: Resource, spreadsheet_id: str, sheet_name: str, width: int, height: int
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


# Creates a blank new spreadsheet
def create_blank_spreadsheet(
    service: Resource, title: str, sheet_name: str, width: int, height: int
) -> Optional[str]:
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


# Creates a new spreadsheet, made of only the results sheet and its basic columns
def create_spreadsheet(service: Resource, title: str) -> Optional[str]:
    # Create a new spreadsheet and add the initial columns
    spreadsheet_id: str = create_blank_spreadsheet(service, title, "Summary", 50, 100)

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
                "OS: STDEV 50",
                "OS: STDEV 90",
                "OS: Average 50",
                "OS: Average 90",
                "OS: RSD 50",
                "OS: RSD 90",
                "",
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


# Returns all the operation categories for the given workload
def get_workload_operation_categories(workload: str) -> list[str] | None:
    category_list: Optional[list[str]] = None

    spec_list: list[dict] = get_category_operation_map()
    for spec in spec_list:
        if spec["workload"] == workload:
            category_list = []
            for category_name in spec["categories"].keys():
                category_list.append(category_name)

    return category_list


# Returns all the operations for the given workload
def get_workload_operations(workload: str) -> list[str] | None:
    operation_list: Optional[list[str]] = None

    spec_list: list[dict] = get_category_operation_map()
    for spec in spec_list:
        if spec["workload"] == workload:
            operation_list = []
            for category_name in spec["categories"].keys():
                for operation_name in spec["categories"][category_name]:
                    operation_list.append(operation_name)

    return operation_list


# Adds a 'categories' sheet
def add_categories_sheet(service: Resource, spreadsheet_id: str):
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



#       # Determine what's the category range for this specific workload. Note that these indexes
#       # are 1-based
#       result: dict = (
#           service.spreadsheets()
#           .values()
#           .get(spreadsheetId=spreadsheet_id, range="Categories!A:A")
#           .execute()
#       )

#       category_range_start: Optional[int] = None
#       category_range_end: Optional[int] = None

#       category_sheet_row_list: list[list[str]] = result.get("values", [])
#       for row_index, category_sheet_row in enumerate(category_sheet_row_list):
#           if category_sheet_row[0] != workload_name:
#               continue
#           
#           if category_range_start is None:
#               category_range_start = row_index + 1
#               continue

#           category_range_end = row_index + 1

#       if category_range_start is None or category_range_end is None:
#           raise ValueError(
#               f"Failed to determine the category range for the following workload and sheet: {sheet_name}, {workload_name}"
#           )

#       # Add the benchmark data to the Results sheet
#       sheet_and_operation_rows: list[str] = []
#       current_row: int = starting_row_index

#       for operation in benchmark_scenario.operation_list:
#           column1: str
#           column2: str
#           operation_column: str
#           if product_identifier == "os":
#               column1 = "A"
#               column2 = "E"
#               operation_column = "E"

#           else:
#               column1 = "N"
#               column2 = "R"
#               operation_column = "R"

#           row_list: list[str] = [
#               sheet_name,
#               f'=INDIRECT({column1}{current_row}&"!H{current_row}")',
#               f'=CONCATENATE("index_merge_policy=", INDIRECT({column1}{current_row}&"!J{current_row}"), ", max_num_segments=", INDIRECT({column1}{current_row}&"!K{current_row}"), ", bulk_indexing_clients=", INDIRECT({column1}{current_row}&"!L{current_row}"), ", target_throughput=", INDIRECT({column1}{current_row}&"!M{current_row}"), ", number_of_replicas=", INDIRECT({column1}{current_row}&"!N{current_row}"))',
#               f'=INDIRECT({column1}{current_row}&"!I{current_row}")',
#               operation,
#               f"=VLOOKUP({operation_column}{current_row}, Categories!B${category_range_start}:C${category_range_end}, 2, FALSE)",
#               f'=STDEV.S(FILTER(INDIRECT({column1}{current_row}&"!F2:F"),INDIRECT({column1}{current_row}&"!B2:B")<>0,INDIRECT({column1}{current_row}&"!D2:D")={column2}{current_row},INDIRECT({column1}{current_row}&"!E2:E")="service_time"))',
#               f'=STDEV.S(FILTER(INDIRECT({column1}{current_row}&"!G2:G"),INDIRECT({column1}{current_row}&"!B2:B")<>0,INDIRECT({column1}{current_row}&"!D2:D")={column2}{current_row},INDIRECT({column1}{current_row}&"!E2:E")="service_time"))',
#               f'=AVERAGE(FILTER(INDIRECT({column1}{current_row}&"!F2:F"),INDIRECT({column1}{current_row}&"!B2:B")<>0,INDIRECT({column1}{current_row}&"!D2:D")={column2}{current_row},INDIRECT({column1}{current_row}&"!E2:E")="service_time"))',
#               f'=AVERAGE(FILTER(INDIRECT({column1}{current_row}&"!G2:G"),INDIRECT({column1}{current_row}&"!B2:B")<>0,INDIRECT({column1}{current_row}&"!D2:D")={column2}{current_row},INDIRECT({column1}{current_row}&"!E2:E")="service_time"))',
#           ]

#           if product_identifier == "os":
#               row_list = row_list + [
#                   f"=G{current_row}/I{current_row}",
#                   f"=H{current_row}/J{current_row}",
#               ]
#           else:
#               row_list = row_list + [
#                   f"=T{current_row}/V{current_row}",
#                   f"=U{current_row}/W{current_row}",
#               ]

#           sheet_and_operation_rows.append(row_list)
#           current_row += 1

#       request_properties: dict = {
#           "majorDimension": "ROWS",
#           "values": sheet_and_operation_rows,
#       }

#       insert_range: str
#       if product_identifier == "os":
#           insert_range = f"Results!A{starting_row_index}"
#       else:
#           insert_range = f"Results!N{starting_row_index}"

#       service.spreadsheets().values().update(
#           spreadsheetId=spreadsheet_id,
#           range=insert_range,
#           valueInputOption="USER_ENTERED",
#           body=request_properties,
#       ).execute()

#   adjust_sheet_columns(service, spreadsheet_id, sheet_name)

#   # Add the comparison column
#   comparison_rows: list[str] = []
#   current_row = starting_row_index

#   for operation in benchmark_scenario.operation_list:
#       comparison_rows.append(
#           [
#               f"=ABS(J{current_row}-V{current_row})*IF(J{current_row}>V{current_row},-1,1)/((J{current_row}+V{current_row})/2)",
#               f"=V{current_row}/J{current_row}",
#           ]
#       )

#       current_row += 1

#   request_properties: dict = {
#       "majorDimension": "ROWS",
#       "values": comparison_rows,
#   }

#   service.spreadsheets().values().update(
#       spreadsheetId=spreadsheet_id,
#       range=f"Results!AA{starting_row_index}",
#       valueInputOption="USER_ENTERED",
#       body=request_properties,
#   ).execute()

#   # Add the summary
#   operation_count: int = len(benchmark_scenario.operation_list)
#   last_operation_row: int = starting_row_index + operation_count - 1

#   row_list: list[list[str]] = []
#   row_list.append(
#       ["Summary", "", "", "Workload:", workload_name, "", f"=C{starting_row_index}"]
#   )
#   row_list.append(["Total Tasks", str(operation_count)])
#   row_list.append(
#       [
#           "Tasks faster than ES",
#           f'=COUNTIF(AA{starting_row_index}:AA{last_operation_row},">0")',
#       ]
#   )
#   row_list.append(["Categories faster than ES", "Category", "Count", "Total"])

#   for category_name in get_workload_operation_categories(workload_name):
#       row_list.append(
#           [
#               "",
#               category_name,
#               f'=COUNTIFS(F${starting_row_index}:F${last_operation_row}, "{category_name}", AA${starting_row_index}:AA${last_operation_row}, ">0")',
#               f'=COUNTIF(F${starting_row_index}:F${last_operation_row}, "{category_name}")',
#           ]
#       )

#   row_list.append([""])
#   row_list.append(
#       [
#           "Tasks much faster than ES",
#           "Operation",
#           "Amount",
#           "",
#           "Tasks much slower than ES",
#           "Operation",
#           "Amount",
#       ]
#   )

#   current_row: int = starting_row_index + len(row_list)

#   row_list.append(
#       [
#           "",
#           f"=FILTER($E${starting_row_index}:$E${last_operation_row}, AB{starting_row_index}:AB{last_operation_row} > 2)",
#           f"=FILTER(AB${starting_row_index}:AB${last_operation_row}, E${starting_row_index}:E${last_operation_row} = AE{current_row})",
#           "",
#           "",
#           f"=FILTER($E${starting_row_index}:$E${last_operation_row}, AB{starting_row_index}:AB{last_operation_row} < 0.5)",
#           f"=FILTER(AB${starting_row_index}:AB${last_operation_row}, E${starting_row_index}:E${last_operation_row} = AI{current_row})",
#       ]
#   )

#   request_properties: dict = {
#       "majorDimension": "ROWS",
#       "values": row_list,
#   }

#   service.spreadsheets().values().update(
#       spreadsheetId=spreadsheet_id,
#       range=f"Results!AD{starting_row_index}",
#       valueInputOption="USER_ENTERED",
#       body=request_properties,
#   ).execute()

#   # Manually expand the first "Amount" columns
#   # TODO: Any way to make this with a formula?
#   row_list = []
#   for i in range(0, 10):
#       row_list.append(
#           [
#               f"=FILTER(AB${starting_row_index}:AB${last_operation_row}, E${starting_row_index}:E${last_operation_row} = AE{current_row + i})",
#           ]
#       )

#   request_properties: dict = {
#       "majorDimension": "ROWS",
#       "values": row_list,
#   }

#   service.spreadsheets().values().update(
#       spreadsheetId=spreadsheet_id,
#       range=f"Results!AF{current_row}",
#       valueInputOption="USER_ENTERED",
#       body=request_properties,
#   ).execute()

#   row_list = []
#   for i in range(0, 10):
#       row_list.append(
#           [
#               f"=FILTER(AB${starting_row_index}:AB${last_operation_row}, E${starting_row_index}:E${last_operation_row} = AI{current_row + i})",
#           ]
#       )

#   request_properties: dict = {
#       "majorDimension": "ROWS",
#       "values": row_list,
#   }

#   service.spreadsheets().values().update(
#       spreadsheetId=spreadsheet_id,
#       range=f"Results!AJ{current_row}",
#       valueInputOption="USER_ENTERED",
#       body=request_properties,
#   ).execute()

#   adjust_sheet_columns(service, spreadsheet_id, sheet_name)
#   return True


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


# Creates a blank spreadsheet
# Returns the spreadsheet id
def init_spreadsheet(
    creds: Credentials
) -> Tuple[Any|None,str|None]:
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

    # Output spreadsheet URL for ease
    report_url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}"
    print(f"Report URL: {report_url}")

    return True