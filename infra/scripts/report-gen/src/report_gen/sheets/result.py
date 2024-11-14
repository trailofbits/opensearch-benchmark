"""Class for creating Result sheet."""

import logging
from dataclasses import dataclass
from itertools import product

from googleapiclient.discovery import Resource

from .common import (
    adjust_sheet_columns,
    convert_range_to_dict,
    get_sheet_id,
    get_workload_operations,
    get_workloads,
)
from .format.color import (
    comparison as format_color_comparison,
)
from .format.color import (
    rsd as format_color_rsd,
)
from .format.font import (
    bold as format_font_bold,
)
from .format.freeze import (
    col as format_freeze_col,
)
from .format.freeze import (
    row as format_freeze_row,
)
from .format.number import (
    format_float as format_number_float,
)

logger = logging.getLogger(__name__)


@dataclass
class Result:
    """Class for creating Result sheet."""

    service: Resource
    spreadsheet_id: str
    sheet_name: str = "Results"
    sheet_id: int | None = None
    sheet: dict | None = None

    def format(self) -> None:
        """Format Result sheet."""
        requests: list[dict] = []
        range_dict: dict = {}

        # Bold first row
        range_dict = convert_range_to_dict(f"{self.sheet_name}!A1:T1")
        range_dict["sheetId"] = self.sheet_id
        requests.append(format_font_bold(range_dict))

        # Freeze first row
        r = format_freeze_row(self.sheet_id, 1)
        if r is not None:
            requests.append(r)

        # Freeze first four columns
        r = format_freeze_col(self.sheet_id, 4)
        if r is not None:
            requests.append(r)

        # Format numbers
        for cells in ["D2:D", "G2:L", "O2:T"]:
            range_dict = convert_range_to_dict(f"{self.sheet_name}!{cells}")
            range_dict["sheetId"] = self.sheet_id
            requests.append(format_number_float(range_dict))

        # Format ES/OS colors
        for cells in ["D2:D"]:
            range_dict = convert_range_to_dict(f"{self.sheet_name}!{cells}")
            range_dict["sheetId"] = self.sheet_id
            requests.extend(format_color_comparison(range_dict))

        # Format RSD colors
        for cells in ["K2:L", "S2:T"]:
            range_dict = convert_range_to_dict(f"{self.sheet_name}!{cells}")
            range_dict["sheetId"] = self.sheet_id
            requests.append(format_color_rsd(range_dict))

        body = {"requests": requests}
        self.service.spreadsheets().batchUpdate(spreadsheetId=self.spreadsheet_id, body=body).execute()

    def get_workload_operations(
        self, index: int, workload: str, os: str, es: str, operations: list[str]
    ) -> list[list[str]]:
        """Retrieve workload operation results for one OS/ES engine combination."""
        rows: list[list[str]] = []

        # For each operation, retrieve OS/ES engine results
        for op in operations:
            raw_sheet = "raw"

            # Match workload name, non-zeroth run, operation name, and service_time
            base = (
                f"{raw_sheet}!$E$2:$E=$A{index},"
                f"{raw_sheet}!$G$2:$G<>0,"
                f"{raw_sheet}!$H$2:$H=$C{index},"
                f'{raw_sheet}!$I$2:$I="service_time"'
            )

            # Match above, plus OS engine and version
            os_stat = f'{raw_sheet}!$C$2:$C="OS",' f'{raw_sheet}!$D$2:$D="{os}",' + base

            # Match above, plus ES engine and version
            es_stat = f'{raw_sheet}!$C$2:$C="ES",' f'{raw_sheet}!$D$2:$D="{es}",' + base

            cell_os_p50_stdev = f"G{index}"
            cell_os_p90_stdev = f"H{index}"
            cell_os_p50_avg = f"I{index}"
            cell_os_p90_avg = f"J{index}"
            cell_os_p50_rsd = f"K{index}"  # noqa: F841
            cell_os_p90_rsd = f"L{index}"  # noqa: F841

            cell_es_p50_stdev = f"O{index}"
            cell_es_p90_stdev = f"P{index}"
            cell_es_p50_avg = f"Q{index}"
            cell_es_p90_avg = f"R{index}"
            cell_es_p50_rsd = f"S{index}"  # noqa: F841
            cell_es_p90_rsd = f"T{index}"  # noqa: F841

            category = f"=VLOOKUP(C{index}, FILTER(Categories!$B$2:$C, Categories!$A2:$A = $A{index}), 2, FALSE)"

            row: list[str] = [
                workload,  # Workload column
                category,  # Category column
                op,  # Operation column
                f"={cell_es_p90_avg}/{cell_os_p90_avg}",  # ES/OS comparison column
                "",  # Blank column
                os,  # OS version column
                f"=STDEV.S(FILTER({raw_sheet}!$J$2:$J, {os_stat}))",  # p50 stdev
                f"=STDEV.S(FILTER({raw_sheet}!$K$2:$K, {os_stat}))",  # p90 stdev
                f"=AVERAGE(FILTER({raw_sheet}!$J$2:$J, {os_stat}))",  # p50 avg
                f"=AVERAGE(FILTER({raw_sheet}!$K$2:$K, {os_stat}))",  # p90 avg
                f"={cell_os_p50_stdev}/{cell_os_p50_avg}",  # p50 rsd
                f"={cell_os_p90_stdev}/{cell_os_p90_avg}",  # p50 rsd
                "",  # Blank column
                es,  # ES version column
                f"=STDEV.S(FILTER({raw_sheet}!$J$2:$J, {es_stat}))",  # p50 stdev
                f"=STDEV.S(FILTER({raw_sheet}!$K$2:$K, {es_stat}))",  # p90 stdev
                f"=AVERAGE(FILTER({raw_sheet}!$J$2:$J, {es_stat}))",  # p50 avg
                f"=AVERAGE(FILTER({raw_sheet}!$K$2:$K, {es_stat}))",  # p90 avg
                f"={cell_es_p50_stdev}/{cell_es_p50_avg}",  # p50 rsd
                f"={cell_es_p90_stdev}/{cell_es_p90_avg}",  # p50 rsd
            ]

            rows.append(row)
            index += 1

        return rows

    def compare_engine(
        self,
        offset: int,
        workload: str,
        operations: list[str],
        engines: dict[str, list[str]],
    ) -> int:
        """Fill in Result sheet with combination of engine comparisons.Returns the number of rows written."""
        if "OS" not in engines:
            logger.error("Error, no OS engines found")
            return 0
        if "ES" not in engines:
            logger.error("Error, no ES engines found")
            return 0

        rows_added: int = 0

        # For each combination of OS/ES engines
        for os, es in product(engines["OS"], engines["ES"]):
            logger.info(f"\tComparing OS {os} versus ES {es}")

            # Retrieve operation comparison
            rows = self.get_workload_operations(offset, workload, os, es, operations)

            # Append table to Result sheet
            request_properties: dict = {
                "majorDimension": "ROWS",
                "values": rows,
            }
            self.service.spreadsheets().values().append(
                spreadsheetId=self.spreadsheet_id,
                range=f"{self.sheet_name}!A1",
                valueInputOption="USER_ENTERED",
                body=request_properties,
            ).execute()

            offset += len(rows)
            rows_added += len(rows)

        return rows_added

    def get(self) -> bool:
        """Process data in raw sheet to fill in Results sheet."""
        # Get sheet ID for Results sheet
        self.sheet_id, self.sheet = get_sheet_id(self.service, self.spreadsheet_id, self.sheet_name)
        if self.sheet_id is None:
            return False

        # Retrieve workload to process and compare
        workloads: dict[str, dict[str, list[str]]] = get_workloads(self.service, self.spreadsheet_id)

        # Offset for keeping track of the number of rows we've filled in
        # We start with 2 because the header row is already filled in
        offset: int = 2

        # For each workload, process engine results
        for workload, engines in workloads.items():
            logger.info(f"Processing {workload}")

            # Retrieve operations for this workload
            operations = get_workload_operations(workload)
            if len(operations) == 0:
                logger.error("Error, no operations found for workload")
                continue

            # Output engine comparisons in Result sheet
            offset += self.compare_engine(offset, workload, operations, engines)

        # Format Result sheet
        self.format()

        # Adjust columns
        adjust_sheet_columns(self.service, self.spreadsheet_id, self.sheet_id, self.sheet)

        return True
