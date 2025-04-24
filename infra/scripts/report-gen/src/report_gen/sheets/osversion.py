"""Class for creating OS Versions sheet."""

import logging
from dataclasses import dataclass

from googleapiclient.discovery import Resource

from .common import (
    adjust_sheet_columns,
    convert_range_to_dict,
    get_category_operation_map,
    get_sheet_id,
    get_workload_operation_categories,
    get_workload_operations,
    get_workloads,
)
from .format.color import (
    color as format_color,
)
from .format.color import (
    comparison as format_color_comparison,
)
from .format.color import get_light_blue, get_light_gray, get_light_yellow
from .format.color import (
    relative_difference as format_color_relative_difference,
)
from .format.font import (
    bold as format_font_bold,
)
from .format.merge import (
    merge as format_merge,
)
from .format.number import (
    format_float as format_number_float,
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

    def create_header(self, os_version: str, es_version: str, workload_str: str) -> list[dict]:  # noqa: PLR0915
        """Fill in header rows & column."""
        requests: list[dict] = []

        # Fill in first row
        rows: list[list[str]] = []
        rows.append(["Results"] + [""] * 5)
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
                range=f"{self.sheet_name}!G1",
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
                range=f"{self.sheet_name}!H1",
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
                range=f"{self.sheet_name}!I1",
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
        rows.append(
            ["Category", "Operation", f"ES {es_version} P90 ST (Median)", "RSD", f"OS {os_version} P90 ST (Median)", "RSD"]
        )
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
        for category, operations in spec["categories"].items():
            rows = []
            rows.append([f"{category}"])
            rows.extend([[""]] * (len(operations) - 1))
            request_properties = {
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

            rows = []
            for operation in operations:
                rows.append([f"{operation}"])
            request_properties = {
                "majorDimension": "ROWS",
                "values": rows,
            }
            result = (
                self.service.spreadsheets()
                .values()
                .append(
                    spreadsheetId=self.spreadsheet_id,
                    range=f"{self.sheet_name}!B{offset}",
                    valueInputOption="USER_ENTERED",
                    body=request_properties,
                )
                .execute()
            )

            offset += len(operations)

        return requests

    def fill(self, os_version: str, es_version: str, workload_str: str) -> list[dict]:
        """Fill in OS Version sheet with data."""
        # Create header
        requests = self.create_header(os_version, es_version, workload_str)

        spec_list: list[dict] = get_category_operation_map()
        for spec in spec_list:
            if spec["workload"] == workload_str:
                break

        logger.info(f"processing {os_version} and {es_version}")

        rows: list[list[str]] = []

        results_sheet = "Results"

        # Match workload name, OS version, and ES version
        base = (
            f'{results_sheet}!$A$2:$A="{workload_str}",'
            f'{results_sheet}!$F$2:$F="{os_version}",'
            f'{results_sheet}!$O$2:$O="{es_version}",'
        )

        def get_base_operation(results_sheet: str, category_cell: str, operation_cell: str) -> str:
            """Create base operation string."""
            return base + f"{results_sheet}!$B$2:$B={category_cell}," + f"{results_sheet}!$C$2:$C={operation_cell}"

        # For each category and operation
        category_index = 3
        operation_index = 3
        for category, operations in spec["categories"].items():
            logger.info(f"Processing category {category}")

            for operation in operations:
                logger.info(f"Processing operation {operation}")

                category_cell = f"$A{category_index}"
                operation_cell = f"$B{operation_index}"
                base_operation = get_base_operation(results_sheet, category_cell, operation_cell)

                es_st_value = f"=FILTER({results_sheet}!$T$2:$T,{base_operation})"
                es_rsd_value = f"=FILTER({results_sheet}!$V$2:$V,{base_operation})"
                os_st_value = f"=FILTER({results_sheet}!$K$2:$K,{base_operation})"
                os_rsd_value = f"=FILTER({results_sheet}!$M$2:$M,{base_operation})"

                es_st_cell = f"$C{operation_index}"
                os_st_cell = f"$E{operation_index}"
                relative_difference = f"=({es_st_cell}-{os_st_cell})/MEDIAN({es_st_cell},{os_st_cell})"
                ratio = f"={es_st_cell}/{os_st_cell}"

                row: list[str] = [
                    es_st_value,
                    es_rsd_value,
                    os_st_value,
                    os_rsd_value,
                    relative_difference,
                    ratio,
                    "",
                ]
                rows.append(row)

                operation_index += 1
            category_index += len(operations)

        # Update table to Summary sheet
        request_properties: dict = {
            "majorDimension": "ROWS",
            "values": rows,
        }
        result = (
            self.service.spreadsheets()
            .values()
            .append(
                spreadsheetId=self.spreadsheet_id,
                range=f"{self.sheet_name}!$C3",
                valueInputOption="USER_ENTERED",
                body=request_properties,
            )
            .execute()
        )
        updated_range = result["updates"]["updatedRange"]

        # Format float numbers
        range_dict = convert_range_to_dict(updated_range)
        range_dict["sheetId"] = self.sheet_id
        requests.append(format_number_float(range_dict))

        # Format Relative Difference colors
        for cells in ["G2:G"]:
            range_dict = convert_range_to_dict(f"{self.sheet_name}!{cells}")
            range_dict["sheetId"] = self.sheet_id
            requests.extend(format_color_relative_difference(range_dict))

        # Format ES/OS colors
        for cells in ["H2:H"]:
            range_dict = convert_range_to_dict(f"{self.sheet_name}!{cells}")
            range_dict["sheetId"] = self.sheet_id
            requests.extend(format_color_comparison(range_dict))

        return requests

    def get(self) -> bool:
        """Retrieve data to fill in OS Version sheets."""
        workload_str = "big5"
        es_version = "8.17.4"
        # NOTE(Evan): These correspond to the OS version sheet names in _create_spreadsheet() in __init__.py
        os_versions = ["2.17.1", "2.18.0", "2.19.1"]

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
            requests = self.fill(osv, es_version, workload_str)

            # Format sheet
            self.format(requests)

            # Adjust columns
            adjust_sheet_columns(self.service, self.spreadsheet_id, self.sheet_id, self.sheet)

        return True
