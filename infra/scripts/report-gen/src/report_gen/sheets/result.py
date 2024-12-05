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
        range_dict = convert_range_to_dict(f"{self.sheet_name}!A1:V1")
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
        for cells in ["D2:D", "H2:M", "Q2:V"]:
            range_dict = convert_range_to_dict(f"{self.sheet_name}!{cells}")
            range_dict["sheetId"] = self.sheet_id
            requests.append(format_number_float(range_dict))

        # Format ES/OS colors
        for cells in ["D2:D"]:
            range_dict = convert_range_to_dict(f"{self.sheet_name}!{cells}")
            range_dict["sheetId"] = self.sheet_id
            requests.extend(format_color_comparison(range_dict))

        # Format RSD colors
        for cells in ["L2:M", "U2:V"]:
            range_dict = convert_range_to_dict(f"{self.sheet_name}!{cells}")
            range_dict["sheetId"] = self.sheet_id
            requests.append(format_color_rsd(range_dict))

        body = {"requests": requests}
        self.service.spreadsheets().batchUpdate(spreadsheetId=self.spreadsheet_id, body=body).execute()

    def get_workload_operations(  # noqa: PLR0913
        self,
        index: int,
        workload: str,
        os: str,
        os_workload_subtype: str,
        es: str,
        es_workload_subtype: str,
        operations: list[str],
    ) -> list[list[str]]:
        """Retrieve workload operation results for one OS/ES engine combination."""
        rows: list[list[str]] = []

        # For each operation, retrieve OS/ES engine results
        for op in operations:
            raw_sheet = "raw"

            # Match workload name, non-zeroth run, operation name, and service_time
            base = (
                f"{raw_sheet}!$E$2:$E=$A{index},"
                f"{raw_sheet}!$H$2:$H<>0,"
                f"{raw_sheet}!$I$2:$I=$C{index},"
                f'{raw_sheet}!$J$2:$J="service_time"'
            )

            # Match above, plus OS engine and version
            os_stat = (
                f'{raw_sheet}!$C$2:$C="OS",'
                f'{raw_sheet}!$D$2:$D="{os}",'
                f'{raw_sheet}!$F$2:$F="{os_workload_subtype}",' + base
            )

            # Match above, plus ES engine and version
            es_stat = (
                f'{raw_sheet}!$C$2:$C="ES",'
                f'{raw_sheet}!$D$2:$D="{es}",'
                f'{raw_sheet}!$F$2:$F="{es_workload_subtype}",' + base
            )

            cell_os_p50_stdev = f"H{index}"
            cell_os_p90_stdev = f"I{index}"
            cell_os_p50_avg = f"J{index}"
            cell_os_p90_avg = f"K{index}"
            cell_os_p50_rsd = f"L{index}"  # noqa: F841
            cell_os_p90_rsd = f"M{index}"  # noqa: F841

            cell_es_p50_stdev = f"Q{index}"
            cell_es_p90_stdev = f"R{index}"
            cell_es_p50_avg = f"S{index}"
            cell_es_p90_avg = f"T{index}"
            cell_es_p50_rsd = f"U{index}"  # noqa: F841
            cell_es_p90_rsd = f"V{index}"  # noqa: F841

            category = f"=VLOOKUP(C{index}, FILTER(Categories!$B$2:$C, Categories!$A2:$A = $A{index}), 2, FALSE)"

            row: list[str] = [
                workload,  # Workload column
                category,  # Category column
                op,  # Operation column
                f"={cell_es_p90_avg}/{cell_os_p90_avg}",  # ES/OS comparison column
                "",  # Blank column
                os,  # OS version column
                os_workload_subtype,  # OS workload subtype column
                f"=STDEV.S(FILTER({raw_sheet}!$K$2:$K, {os_stat}))",  # p50 stdev
                f"=STDEV.S(FILTER({raw_sheet}!$L$2:$L, {os_stat}))",  # p90 stdev
                f"=AVERAGE(FILTER({raw_sheet}!$K$2:$K, {os_stat}))",  # p50 avg
                f"=AVERAGE(FILTER({raw_sheet}!$L$2:$L, {os_stat}))",  # p90 avg
                f"={cell_os_p50_stdev}/{cell_os_p50_avg}",  # p50 rsd
                f"={cell_os_p90_stdev}/{cell_os_p90_avg}",  # p50 rsd
                "",  # Blank column
            ]

            if es:
                row.extend(
                    [
                        es,  # ES version column
                        es_workload_subtype,  # ES workload subtype column
                        f"=STDEV.S(FILTER({raw_sheet}!$K$2:$K, {es_stat}))",  # p50 stdev
                        f"=STDEV.S(FILTER({raw_sheet}!$L$2:$L, {es_stat}))",  # p90 stdev
                        f"=AVERAGE(FILTER({raw_sheet}!$K$2:$K, {es_stat}))",  # p50 avg
                        f"=AVERAGE(FILTER({raw_sheet}!$L$2:$L, {es_stat}))",  # p90 avg
                        f"={cell_es_p50_stdev}/{cell_es_p50_avg}",  # p50 rsd
                        f"={cell_es_p90_stdev}/{cell_es_p90_avg}",  # p50 rsd
                    ]
                )
            # If no ES runs, leave cells blank
            else:
                row.extend([""] * 8)

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
        # If no ES results are considered, still output OS results
        if "ES" not in engines:
            engines["ES"] = [""]

        rows_added: int = 0
        rows: list[list[str]] = []

        # For each combination of OS/ES engines
        for os, es in product(engines["OS"], engines["ES"]):
            logger.info(f"\tComparing OS {os} versus ES {es}")

            # NOTE: Consider not hardcoding this in the future
            if workload == "vectorsearch":
                es_workload_subtype = "lucene-cohere-"

                # Retrieve operation comparison
                result: dict = (
                    self.service.spreadsheets()
                    .values()
                    .get(spreadsheetId=self.spreadsheet_id, range="raw!F2:F")
                    .execute()
                )
                subtypes_array: list[list[str]] = result.get("values", [])
                subtypes = sorted(set({x[0] for x in subtypes_array if x}))
                logger.info(f"Subtypes: {subtypes}")
                for os_workload_subtype in subtypes:
                    # Get size to compare
                    size: str = ""
                    if "-1m" in os_workload_subtype:
                        size = "1m"
                    elif "-10m" in os_workload_subtype:
                        size = "10m"
                    else:
                        size = "1m"

                    row = self.get_workload_operations(
                        offset, workload, os, os_workload_subtype, es, es_workload_subtype + size, operations
                    )
                    offset += len(row)
                    rows_added += len(row)
                    rows.extend(row)
            else:
                rows = self.get_workload_operations(offset, workload, os, "", es, "", operations)
                offset += len(rows)
                rows_added += len(rows)

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

            rows = []

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
        for workload, engines in sorted(workloads.items()):
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
