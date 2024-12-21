"""API for interacting with Google Sheets."""

import logging
import time
from collections.abc import Callable
from functools import wraps
from pathlib import Path
from typing import Any, Concatenate, ParamSpec, TypeVar, cast

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import Resource, build
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)

# Limit access to files created by this app
# See: https://developers.google.com/identity/protocols/oauth2/scopes#sheets
SCOPES = ["https://www.googleapis.com/auth/drive.file"]


def authenticate(credential_path: Path | None, token_path: Path) -> Credentials | None:
    """Authenticate with Google API.

    If a credentials file is passed, create a new token at the provided path and use it to authenticate.
    If no credentials file is passed, use the token at the provided path to authenticate.
    Return None if authorization fails.
    """
    if credential_path is not None:
        authenticate_from_credentials(credential_path, token_path)
    return authenticate_from_token(token_path)


def authenticate_from_credentials(credentials_file_path: Path, token_file_path: Path) -> None:
    """Authenticate a new session using a credentials file and create a token at the given path."""
    flow: InstalledAppFlow = InstalledAppFlow.from_client_secrets_file(credentials_file_path, SCOPES)
    creds: Credentials = flow.run_local_server(port=0)

    with token_file_path.open("w") as token:
        token.write(creds.to_json())


def authenticate_from_token(token_file_path: Path) -> Credentials | None:
    """Restores a previously authenticated session, using a token file."""
    creds: Credentials | None = None

    if not token_file_path.exists():
        logger.error("Missing token file")
        return None

    creds = Credentials.from_authorized_user_file(token_file_path, SCOPES)
    if not creds or not creds.valid:
        logger.error("Authentication has failed")
        return None

    return creds


# T is the return type of the decorated function
# P is a ParamSpec that captures all parameter types
T = TypeVar("T")
P = ParamSpec("P")
TOO_MANY_REQUESTS = 429


def rate_limit(func: Callable[Concatenate[Any, P], T]) -> Callable[Concatenate[Any, P], T]:
    """Catches 429 (Too Many Requests) errors and retries after a minute."""

    @wraps(func)
    def decorator(self: Any, *args: P.args, **kwargs: P.kwargs) -> T:
        max_retries = 5
        delay = 61

        for retry in range(max_retries):
            try:
                return func(self, *args, **kwargs)
            except HttpError as err:
                if err.resp.status != TOO_MANY_REQUESTS or retry == max_retries - 1:
                    raise
                logger.info(f"Rate Limit Exceeded. Retrying in {delay} seconds.")
                time.sleep(delay)
        raise RuntimeError

    return decorator


class SpreadSheetBuilder:
    """Helper for building a google spreadsheet."""

    # TODO(brad): wrap requests to check rate limit #noqa: FIX002, TD003
    service = Resource
    spreadsheet_id: str

    def __init__(self, spreadsheet_name: str, token: Path, credentials: Path | None = None) -> None:
        """Authenticate and create a new spreadsheet to build."""
        creds = authenticate(credentials, token)
        if creds is None:
            msg = "Failed to authenticate the API client"
            logger.error(msg)
            raise RuntimeError(msg)

        # Initialize the api client
        service: Resource = build("sheets", "v4", credentials=creds)
        if service is None:
            msg = "Failed to initialize the API client"
            logger.error(msg)
            raise RuntimeError(msg)

        self.service = service
        self.spreadsheet_id = SpreadSheetBuilder._create_spreadsheet(self.service, spreadsheet_name)

    def create_sheet(self, sheet_name: str) -> "SheetBuilder":
        """Add a sheet to the spreadsheet and return a builder for the new sheet."""
        self._create_sheet(sheet_name)
        return SheetBuilder(sheet_name, self)

    @rate_limit
    def _create_sheet(self, sheet_name: str) -> None:
        """Add a sheet to the spreadsheet."""
        self.service.spreadsheets().batchUpdate(
            spreadsheetId=self.spreadsheet_id, body={"requests": [{"addSheet": {"properties": {"title": sheet_name}}}]}
        ).execute()

    @classmethod
    @rate_limit
    def _create_spreadsheet(cls, service: Resource, spreadsheet_name: str) -> str:
        """Create a new spreadsheet and return its spreadsheetId."""
        spreadsheet: dict = (
            service.spreadsheets()
            .create(
                body={
                    "properties": {
                        "title": spreadsheet_name,
                    },
                },
                fields="spreadsheetId",
            )
            .execute()
        )
        return cast(str, spreadsheet.get("spreadsheetId"))

    @rate_limit
    def get_sheet_id(self, sheet_name: str) -> int | None:
        """Return the sheet ID for the given sheet name."""
        # Get the spreadsheet metadata to find the sheetId
        spreadsheet = self.service.spreadsheets().get(spreadsheetId=self.spreadsheet_id).execute()

        # Find the sheetId by sheet name
        for sheet in spreadsheet["sheets"]:
            if sheet["properties"]["title"] == sheet_name:
                return int(sheet["properties"]["sheetId"])

        return None

    @rate_limit
    def delete_sheet(self, name: str) -> bool:
        """Delete the named sheet if it exists. Returns true if a sheet was deleted."""
        sheet_id = self.get_sheet_id(name)
        if sheet_id is None:
            return False

        self.service.spreadsheets().batchUpdate(
            spreadsheetId=self.spreadsheet_id, body={"requests": [{"deleteSheet": {"sheetId": sheet_id}}]}
        ).execute()

        return True


class SheetBuilder:
    """Helper for building a google sheet."""

    parent: SpreadSheetBuilder
    sheet_name: str

    @property
    def service(self) -> Resource:
        """Get the google sheets service."""
        return self.parent.service

    @property
    def spreadsheet_id(self) -> str:
        """Get the spreadsheet id."""
        return self.parent.spreadsheet_id

    def __init__(self, sheet_name: str, parent: SpreadSheetBuilder) -> None:
        """Authenticate and create a new spreadsheet to build."""
        self.sheet_name = sheet_name
        self.parent = parent

    @rate_limit
    def insert_rows(self, sheet_range: str, rows: list[list[str]]) -> None:
        """Insert rows at the position `sheet_range`.

        `sheet_range` should be a google sheets range. For example "A1" or "B7".
        """
        request_properties: dict = {
            "majorDimension": "ROWS",
            "values": rows,
        }
        self.service.spreadsheets().values().append(
            spreadsheetId=self.spreadsheet_id,
            range=f"{self.sheet_name}!{sheet_range}",
            valueInputOption="USER_ENTERED",
            body=request_properties,
        ).execute()

    @rate_limit
    def get_sheet_id(self) -> int | None:
        """Return the sheet ID for this sheet."""
        return self.parent.get_sheet_id(self.sheet_name)

    def format_builder(self) -> "FormatBuilder":
        """Create a `FormatBuilder` for the specified sheet, used to apply formatting rules."""
        sheet_id = self.get_sheet_id()
        if sheet_id is None:
            raise RuntimeError(f"missing sheet '{self.sheet_name}'")  # noqa: TRY003, EM102
        return FormatBuilder(self, self.sheet_name, sheet_id)

    @rate_limit
    def apply_format(self, fmt: "FormatBuilder") -> None:
        """Apply the supplied format rules to this spreadsheet."""
        # Get metadata about the sheet being formatted
        spreadsheet = self.service.spreadsheets().get(spreadsheetId=self.spreadsheet_id).execute()
        sheet = next(sheet for sheet in spreadsheet["sheets"] if sheet["properties"]["sheetId"] == fmt.sheet_id)
        # Resize columns based on content
        column_count = sheet["properties"].get("gridProperties", {}).get("columnCount", 0)
        fmt.requests += [
            {
                "autoResizeDimensions": {
                    "dimensions": {
                        "sheetId": fmt.sheet_id,
                        "dimension": "COLUMNS",
                        "startIndex": 0,
                        "endIndex": column_count,
                    }
                }
            }
        ]
        self.service.spreadsheets().batchUpdate(
            spreadsheetId=self.spreadsheet_id, body={"requests": fmt.requests}
        ).execute()


class FormatBuilder:
    """Helper for building a set of formatting rules to apply to a spreadsheet."""

    parent: SheetBuilder

    requests: list[dict]
    sheet_id: int
    sheet_name: str

    def __init__(self, parent: SheetBuilder, sheet_name: str, sheet_id: int) -> None:
        self.parent = parent
        self.sheet_id = sheet_id
        self.sheet_name = sheet_name
        self.requests = []

    def apply(self) -> None:
        """Apply the formatting rules."""
        self.parent.apply_format(self)
        self.requests = []

    def bold_font(self, range_str: str) -> None:
        """Make the specified range bold."""
        self.requests.append(
            {
                "repeatCell": {
                    "range": self.range_dict(range_str),
                    "cell": {"userEnteredFormat": {"textFormat": {"bold": True}}},
                    "fields": "userEnteredFormat.textFormat.bold",
                }
            }
        )

    def freeze_row(self, row_count: int) -> None:
        """Freeze the specified rows."""
        self.requests.append(
            {
                "updateSheetProperties": {
                    "properties": {"sheetId": self.sheet_id, "gridProperties": {"frozenRowCount": row_count}},
                    "fields": "gridProperties.frozenRowCount",
                }
            }
        )

    def freeze_col(self, col_count: int) -> None:
        """Freeze the specified columns."""
        self.requests.append(
            {
                "updateSheetProperties": {
                    "properties": {"sheetId": self.sheet_id, "gridProperties": {"frozenColumnCount": col_count}},
                    "fields": "gridProperties.frozenColumnCount",
                }
            }
        )

    def style_float(self, range_str: str) -> None:
        """Style the specified range as floats."""
        self.requests.append(
            {
                "repeatCell": {
                    "range": self.range_dict(range_str),
                    "cell": {"userEnteredFormat": {"numberFormat": {"type": "NUMBER", "pattern": "#,##0.000"}}},
                    "fields": "userEnteredFormat.numberFormat",
                }
            }
        )

    def color_comparison(self, range_str: str) -> None:
        """Apply the red/green comparison conditional format rules to the specified range."""
        range_dict = convert_range_to_dict(f"{self.sheet_name}!{range_str}")
        range_dict["sheetId"] = self.sheet_id

        self.requests += [
            # Value is less than 0.5
            {
                "addConditionalFormatRule": {
                    "rule": {
                        "ranges": [range_dict],
                        "booleanRule": {
                            "condition": {"type": "NUMBER_LESS", "values": [{"userEnteredValue": "0.5"}]},
                            "format": {"backgroundColor": DARK_RED},
                        },
                    },
                    "index": 0,
                }
            },
            # Value is between 0.5 and 1
            {
                "addConditionalFormatRule": {
                    "rule": {
                        "ranges": [range_dict],
                        "booleanRule": {
                            "condition": {
                                "type": "NUMBER_BETWEEN",
                                "values": [{"userEnteredValue": "0.5"}, {"userEnteredValue": "1"}],
                            },
                            "format": {"backgroundColor": LIGHT_RED},
                        },
                    },
                    "index": 1,
                }
            },
            # Value is between 1 and 2
            {
                "addConditionalFormatRule": {
                    "rule": {
                        "ranges": [range_dict],
                        "booleanRule": {
                            "condition": {
                                "type": "NUMBER_BETWEEN",
                                "values": [{"userEnteredValue": "1"}, {"userEnteredValue": "2"}],
                            },
                            "format": {"backgroundColor": LIGHT_GREEN},
                        },
                    },
                    "index": 2,
                }
            },
            # Value is greater than 2
            {
                "addConditionalFormatRule": {
                    "rule": {
                        "ranges": [range_dict],
                        "booleanRule": {
                            "condition": {"type": "NUMBER_GREATER", "values": [{"userEnteredValue": "2"}]},
                            "format": {"backgroundColor": DARK_GREEN},
                        },
                    },
                    "index": 3,
                }
            },
        ]

    def color_relative_difference(self, range_str: str) -> None:
        """Conditionally formats relative difference."""
        self.requests += [
            # Value is less than 0
            {
                "addConditionalFormatRule": {
                    "rule": {
                        "ranges": [self.range_dict(range_str)],
                        "booleanRule": {
                            "condition": {"type": "NUMBER_LESS", "values": [{"userEnteredValue": "0"}]},
                            "format": {"backgroundColor": LIGHT_RED},
                        },
                    },
                    "index": 0,
                }
            },
            # Value is greater than 0
            {
                "addConditionalFormatRule": {
                    "rule": {
                        "ranges": [self.range_dict(range_str)],
                        "booleanRule": {
                            "condition": {"type": "NUMBER_GREATER", "values": [{"userEnteredValue": "0"}]},
                            "format": {"backgroundColor": LIGHT_GREEN},
                        },
                    },
                    "index": 0,
                }
            },
        ]

    def rsd(self, range_str: str) -> None:
        """Apply the RSD style rules to the specified range."""
        self.requests.append(
            {
                "addConditionalFormatRule": {
                    "rule": {
                        "ranges": [self.range_dict(range_str)],
                        "booleanRule": {
                            "condition": {"type": "NUMBER_GREATER", "values": [{"userEnteredValue": "0.05"}]},
                            "format": {"backgroundColor": LIGHT_RED},
                        },
                    },
                    "index": 0,
                }
            }
        )

    def color(self, range_str: str, color: dict) -> None:
        """Color the range."""
        self.requests.append(
            {
                "repeatCell": {
                    "range": self.range_dict(range_str),
                    "cell": {
                        "userEnteredFormat": {
                            "backgroundColor": color,
                        }
                    },
                    "fields": "userEnteredFormat(backgroundColor)",
                }
            }
        )

    def merge(self, range_str: str) -> None:
        """Merge range."""
        self.requests.append({"mergeCells": {"range": self.range_dict(range_str), "mergeType": "MERGE_ALL"}})

    def range_dict(self, range_str: str) -> dict:
        """Convert a range str to a range_dict to be used in a request."""
        range_dict = convert_range_to_dict(f"{self.sheet_name}!{range_str}")
        range_dict["sheetId"] = self.sheet_id
        return range_dict


LIGHT_RED = {"red": 244 / 255, "green": 199 / 255, "blue": 195 / 255}
DARK_RED = {"red": 244 / 255, "green": 102 / 255, "blue": 102 / 255}
LIGHT_GREEN = {"red": 183 / 255, "green": 225 / 255, "blue": 205 / 255}
DARK_GREEN = {"red": 87 / 255, "green": 187 / 255, "blue": 138 / 255}
LIGHT_BLUE = {"red": 207 / 255, "green": 226 / 255, "blue": 243 / 255}
LIGHT_ORANGE = {"red": 252 / 255, "green": 229 / 255, "blue": 205 / 255}
LIGHT_CYAN = {"red": 208 / 255, "green": 224 / 255, "blue": 227 / 255}
LIGHT_PURPLE = {"red": 217 / 255, "green": 210 / 255, "blue": 233 / 255}
LIGHT_YELLOW = {"red": 255 / 255, "green": 242 / 255, "blue": 204 / 255}
LIGHT_GRAY = {"red": 239 / 255, "green": 239 / 255, "blue": 239 / 255}


def convert_range_to_dict(range_str: str) -> dict:
    """Convert range string to dictionary."""
    # Example updated_range: 'Sheet1!A5:D5'
    # Split the sheet name from the range
    cell_range = range_str.split("!")[1] if "!" in range_str else range_str

    # Split start and end cells (e.g., 'A5:D5')
    start_cell, end_cell = cell_range.split(":")

    # Function to convert column letters to index
    def column_to_index(col: str) -> int:
        index = 0
        for char in col:
            index = index * 26 + (ord(char.upper()) - ord("A")) + 1
        return index - 1  # Convert to 0-indexed

    rv: dict = {}

    # Extract the column letters and row numbers
    import re

    m = re.search(r"\d+", start_cell)
    if m:
        start_row = int(m.group()) - 1  # Convert to 0-indexed
        rv["startRowIndex"] = start_row

    m = re.search(r"\d+", end_cell)
    if m:
        end_row = int(m.group())  # No need to subtract 1 since it's non-inclusive
        rv["endRowIndex"] = end_row

    m = re.match(r"[A-Z]+", start_cell)
    if m:
        start_col = m.group()
        start_column_index = column_to_index(start_col)
        rv["startColumnIndex"] = start_column_index

    m = re.match(r"[A-Z]+", end_cell)
    if m:
        end_col = m.group()
        end_column_index = column_to_index(end_col) + 1  # End is non-inclusive, so add 1
        rv["endColumnIndex"] = end_column_index

    # Construct the range dictionary
    return rv
