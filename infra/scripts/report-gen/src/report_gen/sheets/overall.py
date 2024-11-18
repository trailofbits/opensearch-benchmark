"""Class for creating OS Overall Spread sheet."""

import logging
from dataclasses import dataclass

from googleapiclient.discovery import Resource

from .common import (
    get_category_operation_map,
    adjust_sheet_columns,
    get_sheet_id,
    convert_range_to_dict,
    get_workload_operations,
    get_workload_operation_categories,
    get_workloads,
)
from .format.color import (
    color as format_color,
)
from .format.color import get_light_blue, get_light_yellow, get_light_gray
from .format.font import (
    bold as format_font_bold,
)
from .format.merge import (
    merge as format_merge,
)

logger = logging.getLogger(__name__)


@dataclass
class OverallSheet:
    """Class for creating Overall Spread sheet."""

    service: Resource
    spreadsheet_id: str
    sheet_name: str | None = None
    sheet_id: int | None = None
    sheet: dict | None = None

    def format_headers_merge(self, range_list: list[str], color: dict) -> list[dict]:
        """Format header rows."""
        requests: list[dict] = []
        for range_str in range_list:
            range_dict = convert_range_to_dict(range_str)
            range_dict["sheetId"] = self.sheet_id
            requests.append(format_font_bold(range_dict))
            requests.append(format_merge(range_dict))
            requests.append(format_color(range_dict, color))
        return requests

    def format(self, requests: list[dict]) -> None:
        """Format summary sheet."""
        body = {"requests": requests}
        self.service.spreadsheets().batchUpdate(spreadsheetId=self.spreadsheet_id, body=body).execute()

    def create_header(self, os_versions: list[str], es_version: str, workload_str: str) -> list[dict]:
        """Fill in header rows & column."""
        requests: list[dict] = []

        def sheet_exec(sheet_range: str, row_values: list[list[str]]) -> str:
            """Execute USER_ENTERED at the specified range with the specified ROWS values.

            Return the updated range.
            """
            result = (
                self.service.spreadsheets()
                .values()
                .append(
                    spreadsheetId=self.spreadsheet_id,
                    range=f"{self.sheet_name}!{sheet_range}",
                    valueInputOption="USER_ENTERED",
                    body={"majorDimension": "ROWS", "values": row_values},
                )
                .execute()
            )
            return result["updates"]["updatedRange"]

        def format_row(
            sheet_range: str,
            row_value: str,
            width: int,
            color: dict,
        ) -> list[dict]:
            """Create a formatted row.

            E.g. sheets_exec("A1", "Results", 5, get_light_yellow()) merges 5 cells A1-G1,
            sets the value to "Results" and makes the background color light yellow.
            """
            updated_range = sheet_exec(sheet_range, [[row_value] + [""] * (width - 1)])
            return self.format_headers_merge([updated_range], color)

        # first column is labels, 2nd is ES, then 1 col for each OS version
        results_col = "A"
        results_width = 2 + len(os_versions)

        # one columns for each OS version
        rel_col = chr(ord(results_col) + results_width)
        rel_width = len(os_versions)

        # one columns for each OS version
        ratio_col = chr(ord(rel_col) + rel_width)
        ratio_width = len(os_versions)

        # Add first row
        requests += format_row(f"{results_col}1", "Results", results_width, get_light_gray())
        requests += format_row(f"{rel_col}1", "Relative Difference\n(ES-OS)/AVG(ES,OS)", rel_width, get_light_yellow())
        requests += format_row(f"{ratio_col}1", "Ratio ES / OS", ratio_width, get_light_blue())

        # Add second row
        row2_range = sheet_exec(
            "A2",
            [
                ["Operation", f"ES {es_version} P90 ST"]
                + [f"OS {v} P90 ST" for v in os_versions]
                + [f"Relative Difference ES {es_version} vs  OS {v}" for v in os_versions]
                + [f"Ratio ES {es_version} vs  OS {v}" for v in os_versions]
            ],
        )
        range_dict = convert_range_to_dict(row2_range)
        range_dict["sheetId"] = self.sheet_id
        requests.append(format_font_bold(range_dict))
        requests.append(format_color(range_dict, get_light_gray()))

        # Fill in first column labels
        row_offset = 3
        spec = next(spec for spec in get_category_operation_map() if spec["workload"] == workload_str)

        for category, operations in spec["categories"].items():
            updated_range = sheet_exec(f"A{row_offset}", [[f"{category}"]] + [[""]] * (len(operations) - 1))
            # Format
            requests.extend(self.format_headers_merge([updated_range], get_light_gray()))
            row_offset += len(operations)

        return requests

    def fill(self, os_versions: list[str], es_version: str, workload_str: str) -> list[dict]:
        """Fill in sheet with data."""
        # Create header
        requests = self.create_header(os_versions, es_version, workload_str)

        # TODO

        return requests

    def get(self) -> bool:
        """Retrieve data to fill in OS Version sheets."""
        workload_str = "big5"
        es_version = "8.15.0"
        # NOTE(Evan): These correspond to the OS version sheet names in _create_spreadsheet() in __init__.py
        os_versions = ["2.16.0", "2.17.0", "2.18.0"]

        # Retrieve workload to process and compare
        workloads: dict[str, dict[str, list[str]]] = get_workloads(self.service, self.spreadsheet_id)

        if workload_str not in workloads:
            logger.error(f"Error, workload {workload_str} not found.")
            return False

        # Retrieve operations for workload
        operations = get_workload_operations(workload_str)
        if len(operations) == 0:
            logger.error(f"Error, no operations found for workload {workload_str}")
            return False

        # Retrieve operations categories for workload
        categories = get_workload_operation_categories(workload_str)
        if len(categories) == 0:
            logger.error(f"Error, no operation categories found for workload {workload_str}")
            return False

        self.sheet_name = "Overall Spread"
        self.sheet_id, self.sheet = get_sheet_id(self.service, self.spreadsheet_id, self.sheet_name)
        if self.sheet_id is None:
            logger.error(f"Error, sheet {self.sheet_name} not found.")
            return False

        requests = self.fill(os_versions, es_version, workload_str)
        self.format(requests)
        adjust_sheet_columns(self.service, self.spreadsheet_id, self.sheet_id, self.sheet)

        return True
