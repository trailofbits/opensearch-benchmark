"""Class for creating OS Versions sheet."""

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
from .format.color import (
    get_light_blue,
    get_light_yellow,
    get_light_gray
)
from .format.font import (
    bold as format_font_bold,
)
from .format.merge import (
    merge as format_merge,
)

logger = logging.getLogger(__name__)


@dataclass
class OSVersion:
    """Class for creating OS Version sheets."""

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

    def create_header(self, os_version: str, es_version: str, workload_str: str) -> list[dict]:
        """Fills in header rows & column."""
        requests: list[dict] = []

        # Fill in first row
        rows: list[list[str]] = []
        rows.append(["Results"] + [""] * 4)
        request_properties: dict = {
            "majorDimension": "ROWS",
            "values": rows,
        }
        result = (
            self.service.spreadsheets()
            .values()
            .append(
                spreadsheetId=self.spreadsheet_id,
                range=f"{self.sheet_name}!A1",
                valueInputOption="USER_ENTERED",
                body=request_properties,
            )
            .execute()
        )
        updated_range = result["updates"]["updatedRange"]

        # Format header
        requests.extend(self.format_headers_merge([updated_range], get_light_gray()))

        # Add first row columns
        rows = []
        rows.append(["Relative Difference\n(ES-OS)/AVG(ES,OS)"])
        rows.append([""])
        request_properties: dict = {
            "majorDimension": "ROWS",
            "values": rows,
        }
        result = (
            self.service.spreadsheets()
            .values()
            .append(
                spreadsheetId=self.spreadsheet_id,
                range=f"{self.sheet_name}!F1",
                valueInputOption="USER_ENTERED",
                body=request_properties,
            )
            .execute()
        )
        updated_range = result["updates"]["updatedRange"]

        # Format header
        requests.extend(self.format_headers_merge([updated_range], get_light_yellow()))

        # Add first row columns
        rows = []
        rows.append([f"Ratio ES {es_version} / OS {os_version}"])
        rows.append([""])
        request_properties: dict = {
            "majorDimension": "ROWS",
            "values": rows,
        }
        result = (
            self.service.spreadsheets()
            .values()
            .append(
                spreadsheetId=self.spreadsheet_id,
                range=f"{self.sheet_name}!G1",
                valueInputOption="USER_ENTERED",
                body=request_properties,
            )
            .execute()
        )
        updated_range = result["updates"]["updatedRange"]

        # Format header
        requests.extend(self.format_headers_merge([updated_range], get_light_blue()))

        # Add first row columns
        rows = []
        rows.append(["Comments"])
        rows.append([""])
        request_properties: dict = {
            "majorDimension": "ROWS",
            "values": rows,
        }
        result = (
            self.service.spreadsheets()
            .values()
            .append(
                spreadsheetId=self.spreadsheet_id,
                range=f"{self.sheet_name}!H1",
                valueInputOption="USER_ENTERED",
                body=request_properties,
            )
            .execute()
        )
        updated_range = result["updates"]["updatedRange"]

        # Format header
        requests.extend(self.format_headers_merge([updated_range], get_light_gray()))

        # Add second row
        rows = []
        rows.append(["Operation", f"ES {es_version} P90 ST", "RSD", f"OS {os_version} P90 ST", "RSD"])
        request_properties: dict = {
            "majorDimension": "ROWS",
            "values": rows,
        }
        result = (
            self.service.spreadsheets()
            .values()
            .append(
                spreadsheetId=self.spreadsheet_id,
                range=f"{self.sheet_name}!A2",
                valueInputOption="USER_ENTERED",
                body=request_properties,
            )
            .execute()
        )
        updated_range = result["updates"]["updatedRange"]

        # Format header
        range_dict = convert_range_to_dict(updated_range)
        range_dict["sheetId"] = self.sheet_id
        requests.append(format_font_bold(range_dict))
        requests.append(format_color(range_dict, get_light_gray()))

        # Add first column
        spec_list: list[dict] = get_category_operation_map()
        for spec in spec_list:
            if spec["workload"] == workload_str:
                break

        offset = 3
        for category,operations in spec["categories"].items():
            rows = []
            rows.append([f"{category}"])
            rows.extend([[""]] * (len(operations)-1))
            request_properties: dict = {
                "majorDimension": "ROWS",
                "values": rows,
            }
            result = (
                self.service.spreadsheets()
                .values()
                .append(
                    spreadsheetId=self.spreadsheet_id,
                    range=f"{self.sheet_name}!A{offset}",
                    valueInputOption="USER_ENTERED",
                    body=request_properties,
                )
                .execute()
            )
            updated_range = result["updates"]["updatedRange"]

            # Format
            requests.extend(self.format_headers_merge([updated_range], get_light_gray()))

            offset += len(operations)

        return requests

    #TODO
    def fill(self, os_version: str, es_version: str, workload_str: str) -> list[dict]:
        """Fills in OS Version sheet with data."""
        # Create header
        requests = self.create_header(os_version, es_version, workload_str)

        results_name = "Results"

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

        # For each OS version
        for osv in os_versions:
            if osv not in workloads[workload_str]["OS"]:
                continue

            # Get sheet ID for this OS version sheet
            self.sheet_name = f"OS {osv}"
            self.sheet_id, self.sheet = get_sheet_id(self.service, self.spreadsheet_id, self.sheet_name)
            if self.sheet_id is None:
                logger.error(f"Error, sheet {self.sheet_name} not found.")
                continue

            # Fill OS version sheet
            requests = self.fill(osv,es_version,workload_str)

            # Format sheet
            self.format(requests)

            # Adjust columns
            adjust_sheet_columns(self.service, self.spreadsheet_id, self.sheet_id, self.sheet)

        return True
