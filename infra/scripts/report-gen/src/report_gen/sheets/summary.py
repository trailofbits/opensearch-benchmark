"""Class for creating Summary sheet."""

import logging
from dataclasses import dataclass

from googleapiclient.discovery import Resource
from packaging.version import Version

from .common import (
    adjust_sheet_columns,
    convert_range_to_dict,
    get_light_blue,
    get_light_cyan,
    get_light_orange,
    get_light_purple,
    get_light_yellow,
    get_sheet_id,
    get_workload_operation_categories,
    get_workload_operations,
    sheet_add,
)

logger = logging.getLogger(__name__)


@dataclass
class Summary:
    """Class for creating Summary sheet."""

    service: Resource
    spreadsheet_id: str
    sheet_id: int | None = None

    def format_numbers(self) -> dict:
        """Format numbers."""
        return {
            "repeatCell": {
                "range": {
                    "sheetId": self.sheet_id,
                },
                "cell": {"userEnteredFormat": {"numberFormat": {"type": "NUMBER", "pattern": "#,##0.000"}}},
                "fields": "userEnteredFormat.numberFormat",
            }
        }

    def format_color(self, range_str: list[str], color: dict) -> None:
        """Color range."""
        requests: list[dict] = []
        for r in range_str:
            range_dict = convert_range_to_dict(r)
            range_dict["sheetId"] = self.sheet_id
            request = {
                "repeatCell": {
                    "range": range_dict,
                    "cell": {
                        "userEnteredFormat": {
                            "backgroundColor": color,
                        }
                    },
                    "fields": "userEnteredFormat(backgroundColor)",
                }
            }
            requests.append(request)

        body = {"requests": requests}
        self.service.spreadsheets().batchUpdate(spreadsheetId=self.spreadsheet_id, body=body).execute()

    def format_merge(self, range_str: str) -> None:
        """Merge range."""
        range_dict = convert_range_to_dict(range_str)
        range_dict["sheetId"] = self.sheet_id
        requests = [{"mergeCells": {"range": range_dict, "mergeType": "MERGE_ALL"}}]

        body = {"requests": requests}
        self.service.spreadsheets().batchUpdate(spreadsheetId=self.spreadsheet_id, body=body).execute()

    def format_bold(self, range_str: list[str]) -> None:
        """Bold range."""
        requests: list[dict] = []
        for r in range_str:
            range_dict = convert_range_to_dict(r)
            range_dict["sheetId"] = self.sheet_id
            request = {
                    "repeatCell": {
                        "range": range_dict,
                        "cell": {"userEnteredFormat": {"textFormat": {"bold": True}}},
                        "fields": "userEnteredFormat.textFormat.bold",
                    }
                }
            requests.append(request)

        body = {"requests": requests}
        self.service.spreadsheets().batchUpdate(spreadsheetId=self.spreadsheet_id, body=body).execute()

    def format(self) -> None:
        """Format Summary sheet."""
        requests = []
        requests.append(self.format_numbers())

        body = {"requests": requests}
        self.service.spreadsheets().batchUpdate(spreadsheetId=self.spreadsheet_id, body=body).execute()

    def create_stats_table(self, workloads: dict[str, dict[str, list[str]]], offset: int) -> int:
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
                range=f"Summary!A{offset}",
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
                range=f"Summary!A{offset}",
                valueInputOption="USER_ENTERED",
                body=request_properties,
            )
            .execute()
        )
        offset += result["updates"]["updatedRows"]
        rows_added += result["updates"]["updatedRows"]
        updated_range = result["updates"]["updatedRange"]
        self.format_bold([updated_range])
        self.format_merge(updated_range)
        self.format_color([updated_range], get_light_blue())

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
        self.service.spreadsheets().values().append(
            spreadsheetId=self.spreadsheet_id,
            range=f"Summary!A{offset}",
            valueInputOption="USER_ENTERED",
            body=request_properties,
        ).execute()

        return rows_added

    def create_all_categories_table(self, workloads: dict[str, dict[str, list[str]]], offset: int) -> int:
        """Create a table summarizing all categories."""
        rows: list[list[str]] = []
        rows_added: int = 0
        header: list[str] = []

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
                range=f"Summary!A{offset}",
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
                range=f"Summary!A{offset}",
                valueInputOption="USER_ENTERED",
                body=request_properties,
            )
            .execute()
        )
        offset += result["updates"]["updatedRows"]
        rows_added += result["updates"]["updatedRows"]
        updated_range = result["updates"]["updatedRange"]
        self.format_bold([updated_range])
        self.format_merge(updated_range)
        self.format_color([updated_range], get_light_blue())

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
                range=f"Summary!$A{offset}",
                valueInputOption="USER_ENTERED",
                body=request_properties,
            )
            .execute()
        )
        offset += result["updates"]["updatedRows"]
        rows_added += result["updates"]["updatedRows"]

        return rows_added

    def create_summary_table(self, workload: str, os_version: str, es_version: str) -> tuple[list[list[str]], list[int]]:
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

        return rows,header_rows

    def create_summary_tables(self, workload: str, engines: dict[str, list[str]], index: int) -> int:
        """Create summary tables for each engine for this workload."""
        if "OS" not in engines:
            logging.error("Error, no OS engines found")
            return index
        if "ES" not in engines:
            logging.error("Error, no ES engines found")
            return index

        rows: list[list[str]] = []

        # Get most recent version of os_version
        os_version = engines["OS"][-1]

        header_ranges: list[str] = []

        cell = "I"
        for es_version in engines["ES"]:
            # Retrieve operation comparison
            col,header_rows = self.create_summary_table(workload, os_version, es_version)

            # Keep track of where headers are
            for h in header_rows:
                end_cell = sheet_add(cell,2)
                header_ranges.append(f"Summary!{cell}{index+h}:{end_cell}{index+h}")

            # Increment column
            cell = sheet_add(cell,4)

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
            range=f"Summary!$I{index}",
            valueInputOption="USER_ENTERED",
            body=request_properties,
        ).execute()

        self.format_bold(header_ranges)
        self.format_color(header_ranges, get_light_blue())

        return index + len(rows)

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

    def create_overview_table(self, workloads: dict[str, dict[str, list[str]]]) -> int:
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
                range="Summary!A1",
                valueInputOption="USER_ENTERED",
                body=request_properties,
            )
            .execute()
        )
        rows_added += result["updates"]["updatedRows"]
        updated_range = result["updates"]["updatedRange"]
        self.format_bold([updated_range])
        self.format_color([updated_range], get_light_blue())

        colors = [
            get_light_orange(),
            get_light_cyan(),
            get_light_purple(),
            get_light_yellow(),
        ]

        index = 2

        for e, (workload, engines) in enumerate(workloads.items()):
            rows: list[list[str]] = []
            row, index = self.get_workload_engines(workload, engines, index)
            rows.extend(row)

            color = colors[e % len(colors)]

            # Add table to Result sheet
            request_properties: dict = {
                "majorDimension": "ROWS",
                "values": rows,
            }
            result = (
                self.service.spreadsheets()
                .values()
                .append(
                    spreadsheetId=self.spreadsheet_id,
                    range="Summary!A1",
                    valueInputOption="USER_ENTERED",
                    body=request_properties,
                )
                .execute()
            )
            rows_added += result["updates"]["updatedRows"]
            updated_range = result["updates"]["updatedRange"]
            self.format_color([updated_range], color)

        return rows_added

    def get_workloads(self) -> dict[str, dict[str, list[str]]]:
        """Retrieve tuples of (engine,version,workload) for benchmarks in the spreadsheet."""
        rv: dict[str, dict[str, list[str]]] = {}

        result: dict = (
            self.service.spreadsheets().values().get(spreadsheetId=self.spreadsheet_id, range="Results!A2:N").execute()
        )
        row_list: list[list[str]] = result.get("values", [])
        for row in row_list:
            workload, _, _, _, _, os_version, _, _, _, _, _, _, _, es_version = row
            if workload not in rv:
                rv[workload] = {}

            if "OS" not in rv[workload]:
                rv[workload]["OS"] = []
            if os_version not in rv[workload]["OS"]:
                rv[workload]["OS"].append(os_version)
            rv[workload]["OS"].sort(key=Version)

            if "ES" not in rv[workload]:
                rv[workload]["ES"] = []
            if es_version not in rv[workload]["ES"]:
                rv[workload]["ES"].append(es_version)
            rv[workload]["ES"].sort(key=Version)

        return rv

    def get(self) -> bool:
        """Process data in Results sheet to fill in Summary sheet."""
        # Get sheet ID for Results sheet
        self.sheet_id = get_sheet_id(self.service, self.spreadsheet_id, "Summary")

        # Retrieve workload to process and compare
        workloads: dict[str, dict[str, list[str]]] = self.get_workloads()

        offset = 1

        # Create overview table
        offset += self.create_overview_table(workloads)

        # For each workload, summarize results
        index = 1
        for workload, engines in workloads.items():
            logger.info(f"Summarizing {workload}")
            index = self.create_summary_tables(workload, engines, index)

        # Create all categories table
        offset += self.create_all_categories_table(workloads, offset)

        # Create stats table
        self.create_stats_table(workloads, offset)

        # Format Summary sheet
        self.format()

        # Adjust columns
        adjust_sheet_columns(self.service, self.spreadsheet_id, "Summary")

        return True
