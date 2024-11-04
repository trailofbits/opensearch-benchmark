"""Class for creating Summary sheet."""

import logging
from dataclasses import dataclass

from googleapiclient.discovery import Resource

from .common import get_workload_operation_categories, get_workload_operations

logger = logging.getLogger(__name__)


@dataclass
class Summary:
    """Class for creating Summary sheet."""

    service: Resource
    spreadsheet_id: str

    def create_stats_table(self, workloads: dict[str, dict[str, set[str]]]) -> None:
        """Create a table summarizing all statistics."""
        rows: list[list[str]] = []

        # Find versions to compare
        offset = 1
        for engines in workloads.values():
            os_version = sorted(engines["OS"])[0]
            es_version = sorted(engines["ES"])[0]
            offset += len(engines["OS"])
            offset += len(engines["ES"])
            break
        offset *= len(workloads.keys())

        rows.append([])
        rows.append(["", f"Statistics comparing: OS v{os_version} and ES v{es_version}", "", ""])
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

    def create_all_categories_table(self, workloads: dict[str, dict[str, set[str]]]) -> None:
        """Create a table summarizing all categories."""
        rows: list[list[str]] = []

        # Find versions to compare
        for engines in workloads.values():
            os_version = sorted(engines["OS"])[0]
            es_version = sorted(engines["ES"])[0]
            break

        # Find category counts and totals for each workload
        all_categories: set[str] = set()
        for workload in workloads:
            categories = get_workload_operation_categories(workload)
            all_categories.update(categories)

        count_str = f'Results!$F$2:$F,"{os_version}",Results!$N$2:$N,"{es_version}"'

        rows.append([])
        rows.append(
            [
                "",
                f"All Categories: OS v{os_version} is Faster than ES v{es_version}",
                "",
                "",
            ]
        )
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
        rows.append([])

        size = len(all_categories) + 1
        rows.append(
            [
                "Total",
                f'=SUM(INDIRECT( ADDRESS(ROW()-{size},COLUMN())&":"&ADDRESS(ROW()-2,COLUMN()) ))',
                f'=SUM(INDIRECT( ADDRESS(ROW()-{size},COLUMN())&":"&ADDRESS(ROW()-2,COLUMN()) ))',
                "=INDIRECT(ADDRESS(ROW(),COLUMN()-2)) * 100 / INDIRECT(ADDRESS(ROW(),COLUMN()-1))",
            ]
        )
        rows.append([])

        # Update table to Summary sheet
        request_properties: dict = {
            "majorDimension": "ROWS",
            "values": rows,
        }
        self.service.spreadsheets().values().append(
            spreadsheetId=self.spreadsheet_id,
            range="Summary!$A1",
            valueInputOption="USER_ENTERED",
            body=request_properties,
        ).execute()

    def create_summary_table(self, workload: str, os_version: str, es_version: str) -> list[list[str]]:
        """Create a summary table for a workload and OS vs. ES engine version."""
        rows: list[list[str]] = []

        number_of_operations = len(get_workload_operations(workload))

        filter_str = f'Results!$A$2:$A="{workload}",Results!$F$2:$F="{os_version}",Results!$N$2:$N="{es_version}"'
        count_str = f'Results!$A$2:$A,"{workload}",Results!$F$2:$F,"{os_version}",Results!$N$2:$N,"{es_version}"'

        # Add overview of results
        rows.append([f"{workload}", f"ES v{es_version}", ""])
        rows.append(["Total Tasks", f"=ROWS(UNIQUE(FILTER(Results!$C$2:$C,{filter_str})))"])
        rows.append(["Tasks faster than ES", f'=COUNTIFS({count_str}, Results!$D$2:$D,">1")'])
        rows.append(["Fast Outliers (> 2)", f'=COUNTIFS({count_str}, Results!$D$2:$D,">2")'])
        rows.append(["Slow Outliers (< 0.5)", f'=COUNTIFS({count_str}, Results!$D$2:$D,"<0.5")'])
        rows.append([])

        # Add categories OS is faster
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
        rows.append([])
        size = len(categories) + 1
        rows.append(
            [
                "Total",
                f'=SUM(INDIRECT( ADDRESS(ROW()-{size},COLUMN())&":"&ADDRESS(ROW()-2,COLUMN()) ))',
                f'=SUM(INDIRECT( ADDRESS(ROW()-{size},COLUMN())&":"&ADDRESS(ROW()-2,COLUMN()) ))',
            ]
        )
        rows.append([])

        # Add operations OS is faster
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
            rows.append([])  # noqa: PERF401
        rows.append([])

        # Add operations OS is slower
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
            rows.append([])  # noqa: PERF401
        rows.append([])

        return rows

    def create_summary_tables(self, workload: str, engines: dict[str, set[str]], index: int) -> int:
        """Create summary tables for each engine for this workload."""
        if "OS" not in engines:
            logging.error("Error, no OS engines found")
            return index
        if "ES" not in engines:
            logging.error("Error, no ES engines found")
            return index

        rows: list[list[str]] = []

        # Get most recent version of os_version
        os_version = sorted(engines["OS"])[0]

        for es_version in sorted(engines["ES"], reverse=True):
            # Retrieve operation comparison
            col = self.create_summary_table(workload, os_version, es_version)
            rows.extend(col)

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

        return index + len(rows)

    def get_workload_engines(
        self, workload: str, engines: dict[str, set[str]], index: int
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

    def create_overview_table(self, workloads: dict[str, dict[str, set[str]]]) -> int:
        """Create Overview table in Summary sheet."""
        rows: list[list[str]] = []

        rows.append(["Engine", "Version", "Workload", "Number of Tests"])

        index = 2

        for workload, engines in workloads.items():
            row, index = self.get_workload_engines(workload, engines, index)
            rows.extend(row)

        # Add table to Result sheet
        request_properties: dict = {
            "majorDimension": "ROWS",
            "values": rows,
        }
        self.service.spreadsheets().values().update(
            spreadsheetId=self.spreadsheet_id,
            range="Summary!A1",
            valueInputOption="USER_ENTERED",
            body=request_properties,
        ).execute()

        return len(rows)

    def get_workloads(self) -> dict[str, dict[str, set[str]]]:
        """Retrieve tuples of (engine,version,workload) for benchmarks in the spreadsheet."""
        rv: dict[str, dict[str, set[str]]] = {}

        result: dict = (
            self.service.spreadsheets().values().get(spreadsheetId=self.spreadsheet_id, range="Results!A2:N").execute()
        )
        row_list: list[list[str]] = result.get("values", [])
        for row in row_list:
            workload, _, _, _, _, os_version, _, _, _, _, _, _, _, es_version = row
            if workload not in rv:
                rv[workload] = {}

            if "OS" not in rv[workload]:
                rv[workload]["OS"] = set()
            rv[workload]["OS"].add(os_version)

            if "ES" not in rv[workload]:
                rv[workload]["ES"] = set()
            rv[workload]["ES"].add(es_version)

        return rv

    def get(self) -> bool:
        """Process data in Results sheet to fill in Summary sheet."""
        # Retrieve workload to process and compare
        workloads: dict[str, dict[str, set[str]]] = self.get_workloads()

        # Create overview table
        self.create_overview_table(workloads)

        # For each workload, summarize results
        index = 1
        for workload, engines in workloads.items():
            logger.info(f"Summarizing {workload}")
            index = self.create_summary_tables(workload, engines, index)

        # Create all categories table
        self.create_all_categories_table(workloads)

        # Create stats table
        self.create_stats_table(workloads)

        return True
