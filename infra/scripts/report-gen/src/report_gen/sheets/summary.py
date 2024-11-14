"""Class for creating Summary sheet."""

import logging
from dataclasses import dataclass

from googleapiclient.discovery import Resource

from .common import (
    adjust_sheet_columns,
    column_add,
    convert_range_to_dict,
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
from .format.color import (
    get_light_blue,
    get_light_cyan,
    get_light_orange,
    get_light_purple,
    get_light_yellow,
)
from .format.font import (
    bold as format_font_bold,
)
from .format.merge import (
    merge as format_merge,
)

logger = logging.getLogger(__name__)


@dataclass
class Summary:
    """Class for creating Summary sheet."""

    service: Resource
    spreadsheet_id: str
    sheet_name: str = "Summary"
    sheet_id: int | None = None
    sheet: dict | None = None

    def format_workload(self, ranges: list[str]) -> list[dict]:
        """Format workload rows."""
        # Get colors for coloring workloads
        colors = [
            get_light_orange(),
            get_light_cyan(),
            get_light_purple(),
            get_light_yellow(),
        ]

        # Format ranges with colors
        requests: list[dict] = []
        for e, range_str in enumerate(ranges):
            range_dict = convert_range_to_dict(range_str)
            range_dict["sheetId"] = self.sheet_id
            color = colors[e % len(colors)]
            requests.append(format_color(range_dict, color))
        return requests

    def format_headers(self, range_list: list[str]) -> list[dict]:
        """Format header rows."""
        requests: list[dict] = []
        for range_str in range_list:
            range_dict = convert_range_to_dict(range_str)
            range_dict["sheetId"] = self.sheet_id
            requests.append(format_font_bold(range_dict))
            requests.append(format_color(range_dict, get_light_blue()))
        return requests

    def format_headers_merge(self, range_list: list[str]) -> list[dict]:
        """Format header rows."""
        requests: list[dict] = []
        for range_str in range_list:
            range_dict = convert_range_to_dict(range_str)
            range_dict["sheetId"] = self.sheet_id
            requests.append(format_font_bold(range_dict))
            requests.append(format_merge(range_dict))
            requests.append(format_color(range_dict, get_light_blue()))
        return requests

    def format(self, requests: list[dict]) -> None:
        """Format summary sheet."""
        body = {"requests": requests}
        self.service.spreadsheets().batchUpdate(spreadsheetId=self.spreadsheet_id, body=body).execute()

    def create_es_operation_compare_table(
        self, workload_str: str, workload: dict[str, list[str]], offset: int
    ) -> tuple[int, list[dict]]:
        """Create a tables comparing ES versions operation speeds."""
        rows: list[list[str]] = []
        rows_added: int = 0

        # Compare ES versions to latest OS version
        os_version = workload["OS"][-1]
        num_es_versions = len(workload["ES"])

        # Add space
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
                range=f"{self.sheet_name}!A{offset}",
                valueInputOption="USER_ENTERED",
                body=request_properties,
            )
            .execute()
        )
        offset += result["updates"]["updatedRows"]
        rows_added += result["updates"]["updatedRows"]

        # Add header row
        rows: list[list[str]] = []
        rows.append([f"Tasks where OS is faster ({workload_str})"] + [""] * num_es_versions)
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
        offset += result["updates"]["updatedRows"]
        rows_added += result["updates"]["updatedRows"]
        updated_range = result["updates"]["updatedRange"]

        # Format header
        requests = self.format_headers_merge([updated_range])

        # Add data
        rows: list[list[str]] = []

        rows.append(["ES Version"] + workload["ES"])
        operations = get_workload_operations(workload_str)
        for op in sorted(operations):
            row: list[str] = []
            row.append(op)

            for e, es_version in enumerate(workload["ES"]):
                filter_str = (
                    f'Results!$A$2:$A="{workload_str}",Results!$F$2:$F="{os_version}",Results!$N$2:$N="{es_version}"'
                )
                row.append(
                    f"=FILTER(Results!$D2:D, {filter_str}, Results!$C2:C = INDIRECT(ADDRESS(ROW(), COLUMN()-1-{e})))"
                )

            rows.append(row)

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
        offset += result["updates"]["updatedRows"]
        rows_added += result["updates"]["updatedRows"]
        updated_range = result["updates"]["updatedRange"]

        # Add formula
        range_dict = convert_range_to_dict(updated_range)
        range_dict["sheetId"] = self.sheet_id
        requests.extend(format_color_comparison(range_dict))

        return rows_added, requests

    def create_es_task_compare_table(
        self, workload_str: str, workload: dict[str, list[str]], offset: int
    ) -> tuple[int, list[dict]]:
        """Create a tables comparing ES versions task speeds."""
        rows: list[list[str]] = []
        rows_added: int = 0

        # Compare ES versions to latest OS version
        os_version = workload["OS"][-1]
        num_es_versions = len(workload["ES"])

        # Add space
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
                range=f"{self.sheet_name}!A{offset}",
                valueInputOption="USER_ENTERED",
                body=request_properties,
            )
            .execute()
        )
        offset += result["updates"]["updatedRows"]
        rows_added += result["updates"]["updatedRows"]

        # Add header row
        rows: list[list[str]] = []
        rows.append([f"Task Speed ({workload_str})"] + [""] * num_es_versions)
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
        offset += result["updates"]["updatedRows"]
        rows_added += result["updates"]["updatedRows"]
        updated_range = result["updates"]["updatedRange"]

        # Format header
        requests = self.format_headers_merge([updated_range])

        # Add data
        rows: list[list[str]] = []

        rows.append(["ES Version"] + workload["ES"])

        row: list[str] = []
        row.append("Tasks faster than ES")
        for es_version in workload["ES"]:
            count_str = (
                f'Results!$A$2:$A,"{workload_str}",Results!$F$2:$F,"{os_version}",Results!$N$2:$N,"{es_version}"'
            )
            row.append(f'=COUNTIFS({count_str}, Results!$D$2:$D,">1")')
        rows.append(row)

        row: list[str] = []
        row.append("Fast Outliers (> 2)")
        for es_version in workload["ES"]:
            count_str = (
                f'Results!$A$2:$A,"{workload_str}",Results!$F$2:$F,"{os_version}",Results!$N$2:$N,"{es_version}"'
            )
            row.append(f'=COUNTIFS({count_str}, Results!$D$2:$D,">2")')
        rows.append(row)

        row: list[str] = []
        row.append("Slow Outliers (< 0.5)")
        for es_version in workload["ES"]:
            count_str = (
                f'Results!$A$2:$A,"{workload_str}",Results!$F$2:$F,"{os_version}",Results!$N$2:$N,"{es_version}"'
            )
            row.append(f'=COUNTIFS({count_str}, Results!$D$2:$D,"<0.5")')
        rows.append(row)

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
        offset += result["updates"]["updatedRows"]
        rows_added += result["updates"]["updatedRows"]

        return rows_added, requests

    def create_es_category_compare_table(
        self, workload_str: str, workload: dict[str, list[str]], offset: int
    ) -> tuple[int, list[dict]]:
        """Create a tables comparing ES versions task categories."""
        rows: list[list[str]] = []
        rows_added: int = 0

        # Compare ES versions to latest OS version
        os_version = workload["OS"][-1]
        num_es_versions = len(workload["ES"])

        # Add space
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
                range=f"{self.sheet_name}!A{offset}",
                valueInputOption="USER_ENTERED",
                body=request_properties,
            )
            .execute()
        )
        offset += result["updates"]["updatedRows"]
        rows_added += result["updates"]["updatedRows"]

        # Add header row
        rows: list[list[str]] = []
        rows.append([f"Task Categories where OS is faster ({workload_str})"] + [""] * num_es_versions)
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
        offset += result["updates"]["updatedRows"]
        rows_added += result["updates"]["updatedRows"]
        updated_range = result["updates"]["updatedRange"]

        # Format header
        requests = self.format_headers_merge([updated_range])

        # Add data
        rows: list[list[str]] = []

        rows.append(["ES Version"] + workload["ES"])
        categories = get_workload_operation_categories(workload_str)
        for category in sorted(categories):
            row: list[str] = []
            row.append(category)

            for e, es_version in enumerate(workload["ES"]):
                count_str = (
                    f'Results!$A$2:$A,"{workload_str}",Results!$F$2:$F,"{os_version}",Results!$N$2:$N,"{es_version}"'
                )
                row.append(
                    f'=COUNTIFS({count_str}, Results!$B$2:$B,INDIRECT(ADDRESS(ROW(),COLUMN()-1-{e})), Results!$D$2:$D,">1")'  # noqa: E501
                )

            rows.append(row)

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
        offset += result["updates"]["updatedRows"]
        rows_added += result["updates"]["updatedRows"]

        return rows_added, requests

    def create_es_compare_tables(
        self, workload_str: str, workload: dict[str, list[str]], offset: int
    ) -> tuple[int, list[dict]]:
        """Create a tables comparing ES versions."""
        requests: list[dict] = []

        o, r = self.create_es_category_compare_table(workload_str, workload, offset)
        offset += o
        requests.extend(r)

        o, r = self.create_es_task_compare_table(workload_str, workload, offset)
        offset += o
        requests.extend(r)

        o, r = self.create_es_operation_compare_table(workload_str, workload, offset)
        offset += o
        requests.extend(r)

        return offset, requests

    def create_stats_table(self, workloads: dict[str, dict[str, list[str]]], offset: int) -> tuple[int, list[dict]]:
        """Create a table summarizing all statistics."""
        rows: list[list[str]] = []
        rows_added: int = 0

        # Find versions to compare
        for engines in workloads.values():
            os_version = engines["OS"][-1]
            es_version = engines["ES"][-1]

        # Add space
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
                range=f"{self.sheet_name}!A{offset}",
                valueInputOption="USER_ENTERED",
                body=request_properties,
            )
            .execute()
        )
        offset += result["updates"]["updatedRows"]
        rows_added += result["updates"]["updatedRows"]

        # Add header row
        rows: list[list[str]] = []
        rows.append([f"Statistics comparing: OS v{os_version} and ES v{es_version}", "", "", "", "", "", ""])
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
        offset += result["updates"]["updatedRows"]
        rows_added += result["updates"]["updatedRows"]
        updated_range = result["updates"]["updatedRange"]

        # Format header
        requests = self.format_headers_merge([updated_range])

        # Add data
        rows: list[list[str]] = []

        rows.append(["ES/OS", "Average", "Median", "Max", "Min", "Stdev", "Variance"])

        filter_faster = f'Results!$F$2:$F="{os_version}",Results!$N$2:$N="{es_version}",Results!$D$2:$D>1'
        filter_slower = f'Results!$F$2:$F="{os_version}",Results!$N$2:$N="{es_version}",Results!$D$2:$D<1'

        faster_row: list[str] = ["When OS is faster\n(OS service_time is smaller)"]
        faster_row.append(f"=AVERAGE(FILTER(Results!$D$2:$D,{filter_faster}))")
        faster_row.append(f"=MEDIAN(FILTER(Results!$D$2:$D,{filter_faster}))")
        faster_row.append(f"=MAX(FILTER(Results!$D$2:$D,{filter_faster}))")
        faster_row.append(f"=MIN(FILTER(Results!$D$2:$D,{filter_faster}))")
        faster_row.append(f"=STDEV.S(FILTER(Results!$D$2:$D,{filter_faster}))")
        faster_row.append(f"=VAR.S(FILTER(Results!$D$2:$D,{filter_faster}))")
        rows.append(faster_row)

        slower_row: list[str] = ["When OS is slower\n(OS service_time is larger)"]
        slower_row.append(f"=AVERAGE(FILTER(Results!$D$2:$D,{filter_slower}))")
        slower_row.append(f"=MEDIAN(FILTER(Results!$D$2:$D,{filter_slower}))")
        slower_row.append(f"=MAX(FILTER(Results!$D$2:$D,{filter_slower}))")
        slower_row.append(f"=MIN(FILTER(Results!$D$2:$D,{filter_slower}))")
        slower_row.append(f"=STDEV.S(FILTER(Results!$D$2:$D,{filter_slower}))")
        slower_row.append(f"=VAR.S(FILTER(Results!$D$2:$D,{filter_slower}))")
        rows.append(slower_row)

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
                range=f"{self.sheet_name}!A{offset}",
                valueInputOption="USER_ENTERED",
                body=request_properties,
            )
            .execute()
        )
        offset += result["updates"]["updatedRows"]
        rows_added += result["updates"]["updatedRows"]

        return rows_added, requests

    def create_all_categories_table(
        self, workloads: dict[str, dict[str, list[str]]], offset: int
    ) -> tuple[int, list[dict]]:
        """Create a table summarizing all categories."""
        rows: list[list[str]] = []
        rows_added: int = 0

        # Find versions to compare
        for engines in workloads.values():
            os_version = engines["OS"][-1]
            es_version = engines["ES"][-1]
            break

        # Find category counts and totals for each workload
        all_categories: set[str] = set()
        for workload in workloads:
            categories = get_workload_operation_categories(workload)
            all_categories.update(categories)

        count_str = f'Results!$F$2:$F,"{os_version}",Results!$N$2:$N,"{es_version}"'

        # Add space
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
                range=f"{self.sheet_name}!A{offset}",
                valueInputOption="USER_ENTERED",
                body=request_properties,
            )
            .execute()
        )
        offset += result["updates"]["updatedRows"]
        rows_added += result["updates"]["updatedRows"]

        # Add header row
        rows: list[list[str]] = []
        rows.append([f"All Categories: OS v{os_version} is Faster than ES v{es_version}", "", "", ""])
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
        offset += result["updates"]["updatedRows"]
        rows_added += result["updates"]["updatedRows"]
        updated_range = result["updates"]["updatedRange"]

        # Format header
        requests = self.format_headers_merge([updated_range])

        # Add data
        rows: list[list[str]] = []
        rows.append(["Category", "Count", "Total", "Percentage (%)"])
        for category in sorted(all_categories):
            row: list[str] = []
            row.append(category)
            row.append(
                f'=COUNTIFS({count_str}, Results!$B$2:$B,INDIRECT(ADDRESS(ROW(),COLUMN()-1)), Results!$D$2:$D,">1")'
            )
            row.append(f"=COUNTIFS({count_str}, Results!$B$2:$B,INDIRECT(ADDRESS(ROW(),COLUMN()-2)))")
            row.append("=INDIRECT(ADDRESS(ROW(),COLUMN()-2)) * 100 / INDIRECT(ADDRESS(ROW(),COLUMN()-1))")
            rows.append(row)

        size = len(all_categories)
        rows.append(
            [
                "Total",
                f'=SUM(INDIRECT( ADDRESS(ROW()-{size},COLUMN())&":"&ADDRESS(ROW()-1,COLUMN()) ))',
                f'=SUM(INDIRECT( ADDRESS(ROW()-{size},COLUMN())&":"&ADDRESS(ROW()-1,COLUMN()) ))',
                "=INDIRECT(ADDRESS(ROW(),COLUMN()-2)) * 100 / INDIRECT(ADDRESS(ROW(),COLUMN()-1))",
            ]
        )

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
                range=f"{self.sheet_name}!$A{offset}",
                valueInputOption="USER_ENTERED",
                body=request_properties,
            )
            .execute()
        )
        offset += result["updates"]["updatedRows"]
        rows_added += result["updates"]["updatedRows"]

        return rows_added, requests

    def create_summary_table(
        self, workload: str, os_version: str, es_version: str
    ) -> tuple[list[list[str]], list[int]]:
        """Create a summary table for a workload and OS vs. ES engine version."""
        rows: list[list[str]] = []
        header_rows: list[int] = []
        header_row_count = 0

        number_of_operations = len(get_workload_operations(workload))

        filter_str = f'Results!$A$2:$A="{workload}",Results!$F$2:$F="{os_version}",Results!$N$2:$N="{es_version}"'
        count_str = f'Results!$A$2:$A,"{workload}",Results!$F$2:$F,"{os_version}",Results!$N$2:$N,"{es_version}"'

        # Add overview of results
        header_rows.append(header_row_count)
        start_count = len(rows)
        rows.append([f"{workload}", f"ES v{es_version}", ""])
        rows.append(["Total Tasks", f"=ROWS(UNIQUE(FILTER(Results!$C$2:$C,{filter_str})))", ""])
        rows.append(["Tasks faster than ES", f'=COUNTIFS({count_str}, Results!$D$2:$D,">1")', ""])
        rows.append(["Fast Outliers (> 2)", f'=COUNTIFS({count_str}, Results!$D$2:$D,">2")', ""])
        rows.append(["Slow Outliers (< 0.5)", f'=COUNTIFS({count_str}, Results!$D$2:$D,"<0.5")', ""])
        rows.append([""])
        header_row_count += len(rows) - start_count

        # Add categories OS is faster
        header_rows.append(header_row_count)
        start_count = len(rows)
        rows.append(["", f"Categories: OS v{os_version} is Faster", ""])
        rows.append(["Category", "Count", "Total"])

        categories = get_workload_operation_categories(workload)

        row = [f'=SORT(UNIQUE(FILTER(Results!$B$2:$B,Results!$A$2:$A="{workload}")))']
        for _ in categories:
            row.append(
                f'=COUNTIFS({count_str}, Results!$B$2:$B,INDIRECT(ADDRESS(ROW(),COLUMN()-1)), Results!$D$2:$D,">1")'
            )
            row.append(f"=COUNTIFS({count_str}, Results!$B$2:$B,INDIRECT(ADDRESS(ROW(),COLUMN()-2)))")
            rows.append(row)
            row = [""]
        rows.append([""])
        size = len(categories) + 1
        rows.append(
            [
                "Total",
                f'=SUM(INDIRECT( ADDRESS(ROW()-{size},COLUMN())&":"&ADDRESS(ROW()-2,COLUMN()) ))',
                f'=SUM(INDIRECT( ADDRESS(ROW()-{size},COLUMN())&":"&ADDRESS(ROW()-2,COLUMN()) ))',
            ]
        )
        rows.append([""])
        header_row_count += len(rows) - start_count

        # Add operations OS is faster
        header_rows.append(header_row_count)
        start_count = len(rows)
        rows.append(["", f"Operations: OS v{os_version} is Faster", ""])
        rows.append(["Category", "Operation", "ES/OS"])
        rows.append(
            [
                f"=SORT(SORT(FILTER(Results!$B$2:$D, {filter_str}, Results!$D$2:$D > 1), 3, FALSE), 1, TRUE)",
                "",
                "",
            ]
        )
        for _ in range(number_of_operations):
            rows.append([""])  # noqa: PERF401
        rows.append([""])
        header_row_count += len(rows) - start_count

        # Add operations OS is slower
        header_rows.append(header_row_count)
        start_count = len(rows)
        rows.append(["", f"Operations: OS v{os_version} is Slower", ""])
        rows.append(["Category", "Operation", "ES/OS"])
        rows.append(
            [
                f"=SORT(SORT(FILTER(Results!$B$2:$D, {filter_str}, Results!$D$2:$D < 1), 3, FALSE), 1, TRUE)",
                "",
                "",
            ]
        )
        for _ in range(number_of_operations):
            rows.append([""])  # noqa: PERF401
        rows.append([""])

        return rows, header_rows

    def create_summary_tables(
        self, workload: str, engines: dict[str, list[str]], offset: int
    ) -> tuple[int, list[dict]]:
        """Create summary tables for each engine for this workload."""
        if "OS" not in engines:
            logging.error("Error, no OS engines found")
            return 0, []
        if "ES" not in engines:
            logging.error("Error, no ES engines found")
            return 0, []

        rows: list[list[str]] = []

        # Get most recent version of os_version
        os_version = engines["OS"][-1]

        header_ranges: list[str] = []

        cell = "I"
        for es_version in engines["ES"]:
            # Retrieve operation comparison
            col, header_rows = self.create_summary_table(workload, os_version, es_version)

            # Keep track of where headers are
            for h in header_rows:
                end_cell = column_add(cell, 2)
                header_ranges.append(f"{self.sheet_name}!{cell}{offset+h}:{end_cell}{offset+h}")

            # Increment column
            cell = column_add(cell, 4)

            # Append column
            if not rows:
                rows.extend(col)
            else:
                rows = [old + [""] + col[e] for e, old in enumerate(rows)]

        # Append table to Result sheet
        request_properties: dict = {
            "majorDimension": "ROWS",
            "values": rows,
        }
        self.service.spreadsheets().values().update(
            spreadsheetId=self.spreadsheet_id,
            range=f"{self.sheet_name}!$I{offset}",
            valueInputOption="USER_ENTERED",
            body=request_properties,
        ).execute()

        # Format workload headers
        requests = self.format_headers(header_ranges)

        return len(rows), requests

    def get_workload_engines(
        self, workload: str, engines: dict[str, list[str]], index: int
    ) -> tuple[list[list[str]], int]:
        """Retrieve list of engines and versions for a workload."""
        rows: list[list[str]] = []

        raw_sheet = "raw"

        for engine, versions in engines.items():
            for version in versions:
                row: list[str] = [
                    engine,
                    version,
                    workload,
                    f"=COUNTA(IFNA(UNIQUE(FILTER({raw_sheet}!$A$2:$A,{raw_sheet}!$C$2:$C=$A{index},{raw_sheet}!$D$2:$D=$B{index},{raw_sheet}!$E$2:$E=$C{index}))))",
                ]

                index += 1

                rows.append(row)

        return rows, index

    def create_overview_table(self, workloads: dict[str, dict[str, list[str]]]) -> tuple[int, list[dict]]:
        """Create Overview table in Summary sheet."""
        rows: list[list[str]] = []
        rows_added: int = 0

        # Add header row
        rows.append(["Engine", "Version", "Workload", "Number of Tests"])
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
        rows_added += result["updates"]["updatedRows"]
        updated_range = result["updates"]["updatedRange"]

        # Format header cells
        requests = self.format_headers([updated_range])

        index = 2
        workload_ranges: list[str] = []
        for workload, engines in workloads.items():
            rows = []
            row, index = self.get_workload_engines(workload, engines, index)
            rows.extend(row)

            # Add table to Result sheet
            request_properties = {
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
            rows_added += result["updates"]["updatedRows"]
            updated_range = result["updates"]["updatedRange"]
            workload_ranges.append(updated_range)

        # Format workload/engine cells
        requests.extend(self.format_workload(workload_ranges))

        return rows_added, requests

    def get(self) -> bool:
        """Process data in Results sheet to fill in Summary sheet."""
        # Get sheet ID for Results sheet
        self.sheet_id, self.sheet = get_sheet_id(self.service, self.spreadsheet_id, self.sheet_name)
        if self.sheet_id is None:
            return False

        # Retrieve workload to process and compare
        workloads: dict[str, dict[str, list[str]]] = get_workloads(self.service, self.spreadsheet_id)

        # Offset for keeping track of the number of rows we've filled in
        # We start with 1 because there is no header row for this sheet
        offset: int = 1

        # Requests to call
        requests: list[dict] = []

        # Create overview table
        o, r = self.create_overview_table(workloads)
        offset += o
        requests.extend(r)

        # For each workload, summarize results
        workload_offset = 1
        for workload, engines in workloads.items():
            logger.info(f"Summarizing {workload}")
            o, r = self.create_summary_tables(workload, engines, workload_offset)
            workload_offset += o
            requests.extend(r)

        # Create all categories table
        o, r = self.create_all_categories_table(workloads, offset)
        offset += o
        requests.extend(r)

        # Create stats table
        o, r = self.create_stats_table(workloads, offset)
        offset += o
        requests.extend(r)

        # If there are more than 1 ES versions for big5, create tables comparing them
        workload_str = "big5"
        if workload_str in workloads and "ES" in workloads[workload_str] and len(workloads[workload_str]["ES"]) > 1:
            logger.info(f"Comparing ES versions for {workload_str}")
            o, r = self.create_es_compare_tables(workload_str, workloads[workload_str], offset)
            offset += o
            requests.extend(r)

        # Format sheet
        self.format(requests)

        # Adjust columns
        adjust_sheet_columns(self.service, self.spreadsheet_id, self.sheet_id, self.sheet)

        return True
