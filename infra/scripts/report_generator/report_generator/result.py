from pathlib import Path
from typing import Optional
from dataclasses import dataclass

from itertools import product

from report_generator.common import get_workload_operations

from googleapiclient.discovery import Resource

@dataclass
class Result:
    """Class for importing benchmark data"""

    service: Resource
    spreadsheet_id: str

    def get_workload_operations(self, index: int, workload: str, os: str, es: str, operations: list[str]) -> list[list[str]]:
        """Retrieves workload operation results for one OS/ES engine combination"""
        rows: list[list[str]] = []

        # For each operation, retrieve OS/ES engine results
        for op in operations:
            raw_sheet = "raw"

            # Match workload name, non-zeroth run, operation name, and service_time
            base = f"{raw_sheet}!$E$2:$E=$A{index}," \
                   f"{raw_sheet}!$G$2:$G<>0," \
                   f"{raw_sheet}!$H$2:$H=$C{index}," \
                   f"{raw_sheet}!$I$2:$I=\"service_time\""

            # Match above, plus OS engine and version
            os_stat = f"{raw_sheet}!$C$2:$C=\"OS\"," \
                      f"{raw_sheet}!$D$2:$D=\"{os}\"," \
                      + base

            # Match above, plus ES engine and version
            es_stat = f"{raw_sheet}!$C$2:$C=\"ES\"," \
                      f"{raw_sheet}!$D$2:$D=\"{es}\","\
                      + base

            cell_os_p50_stdev = f"G{index}"
            cell_os_p90_stdev = f"H{index}"
            cell_os_p50_avg = f"I{index}"
            cell_os_p90_avg = f"J{index}"
            cell_os_p50_rsd = f"K{index}"
            cell_os_p90_rsd = f"L{index}"

            cell_es_p50_stdev = f"O{index}"
            cell_es_p90_stdev = f"P{index}"
            cell_es_p50_avg = f"Q{index}"
            cell_es_p90_avg = f"R{index}"
            cell_es_p50_rsd = f"S{index}"
            cell_es_p90_rsd = f"T{index}"
            
            row: list[str] = [
                workload,   # Workload column
                f"=VLOOKUP(C{index}, FILTER(Categories!$B$2:$C, Categories!$A2:$A = $A{index}), 2, FALSE)",  # Category column
                op,         # Operation column
                f"={cell_es_p90_avg}/{cell_os_p90_avg}",  # ES/OS comparison column
                "",         # Blank column
                os,   # OS version column
                f"=STDEV.S(FILTER({raw_sheet}!$J$2:$J, {os_stat}))", # p50 stdev
                f"=STDEV.S(FILTER({raw_sheet}!$K$2:$K, {os_stat}))", # p90 stdev
                f"=AVERAGE(FILTER({raw_sheet}!$J$2:$J, {os_stat}))", # p50 avg
                f"=AVERAGE(FILTER({raw_sheet}!$K$2:$K, {os_stat}))", # p90 avg
                f"={cell_os_p50_stdev}/{cell_os_p50_avg}",  # p50 rsd
                f"={cell_os_p90_stdev}/{cell_os_p90_avg}",  # p50 rsd
                "",         # Blank column
                es,   # ES version column
                f"=STDEV.S(FILTER({raw_sheet}!$J$2:$J, {es_stat}))", # p50 stdev
                f"=STDEV.S(FILTER({raw_sheet}!$K$2:$K, {es_stat}))", # p90 stdev
                f"=AVERAGE(FILTER({raw_sheet}!$J$2:$J, {es_stat}))", # p50 avg
                f"=AVERAGE(FILTER({raw_sheet}!$K$2:$K, {es_stat}))", # p90 avg
                f"={cell_es_p50_stdev}/{cell_es_p50_avg}",  # p50 rsd
                f"={cell_es_p90_stdev}/{cell_es_p90_avg}",  # p50 rsd
            ]

            rows.append(row)
            index += 1

        return rows


    def compare_engine(self, offset: int, workload: str, operations: list[str], engines: dict[str,set[str]]) -> int:
        """
        Fills in Result sheet with combination of engine comparisons.
        Returns the number of rows written.
        """

        if "OS" not in engines:
            print("Error, no OS engines found")
            return 0
        if "ES" not in engines:
            print("Error, no ES engines found")
            return 0

        # For each combination of OS/ES engines
        for os,es in product(engines["OS"], engines["ES"]):
            print(f"\tComparing OS {os} versus ES {es}")

            # Retrieve operation comparison
            rows = self.get_workload_operations(offset,workload,os,es,operations)

            # Append table to Result sheet
            request_properties: dict = {
                "majorDimension": "ROWS",
                "values": rows,
            }
            self.service.spreadsheets().values().append(
                spreadsheetId=self.spreadsheet_id,
                range="Results!A1",
                valueInputOption="USER_ENTERED",
                body=request_properties,
            ).execute()

            offset += len(rows)

        return offset


    def get_workloads(self) -> dict[str,dict[str,set[str]]]:
        """Retrieves tuples of (engine,version,workload) for all benchmarks in the spreadsheet"""

        rv: dict[str,dict[str,set[str]]] = {}

        result: dict = (
            self.service.spreadsheets()
            .values()
            .get(spreadsheetId=self.spreadsheet_id, range="raw!C2:E")
            .execute()
        )
        row_list: list[list[str]] = result.get("values", [])
        for index, row in enumerate(row_list):
            engine,version,workload = row
            if workload not in rv:
                rv[workload] = dict()
            if engine not in rv[workload]:
                rv[workload][engine] = set()
            rv[workload][engine].add(version)

        return rv


    def get(self) -> bool:
        """Processes data in raw sheet to fill in Results sheet"""

        # Retrieve workload to process and compare
        workloads: dict[str,dict[str,set[str]]] = self.get_workloads()

        # Offset for keeping track of the number of rows we've filled in
        # We start with 2 because the header row is already filled in
        offset: int = 2

        # For each workload, process engine results
        for workload,engines in workloads.items():
            print(f"Processing {workload}")

            # Retrieve operations for this workload
            operations = get_workload_operations(workload)
            if operations is None:
                print("Error, no operations found for workload")
                continue

            # Output engine comparisons in Result sheet
            offset = self.compare_engine(offset,workload,operations,engines)

        return True

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

