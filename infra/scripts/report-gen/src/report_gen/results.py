"""Calculate Results."""

from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from statistics import mean, median, stdev, variance

from googleapiclient.discovery import Resource

from .download import BenchmarkResult


@dataclass
class Compare:
    """A pair of OS/ES versions to be compared."""

    os_version: str
    es_version: str


@dataclass
class Result:
    """Store Results."""

    workload: str
    category: str
    operation: str

    os_version: str
    os_std_50: float
    os_std_90: float
    os_avg_50: float
    os_avg_90: float
    os_rsd_50: float
    os_rsd_90: float
    es_version: str
    es_std_50: float
    es_std_90: float
    es_avg_50: float
    es_avg_90: float
    es_rsd_50: float
    es_rsd_90: float
    comparison: float


def build_results(data: list[BenchmarkResult], comparisons: list[Compare]) -> list[Result]:
    sub_groups: dict[str, dict[str, list[BenchmarkResult]]] = defaultdict(lambda: defaultdict(list))

    # Filter down to relevant runs, storing rows by their workload and operation
    for row in data:
        # Do not use the first run in our statistics and only include service_time metrics
        if row.Run == "0" or row.MetricName != "service_time":
            continue
        workload = row.Workload
        operation = row.Operation
        sub_groups[workload][operation] += [row]

    results = []
    for workload, operations in sub_groups.items():
        category = "todo"
        for operation, rows in operations.items():
            os_rows = [row for row in rows if row.Engine == "OS"]
            es_rows = [row for row in rows if row.Engine == "ES"]
            for compare in comparisons:
                os_data = [row for row in os_rows if row.EngineVersion == compare.os_version]
                es_data = [row for row in es_rows if row.EngineVersion == compare.es_version]

                def verify_data(data: list[BenchmarkResult]) -> None:
                    """Check assumptions about the data before reporting stats."""
                    if [d.Run for d in data] != ["1", "2", "3", "4"]:
                        msg = f"{workload}-{operation} expected 5 runs but got {[d.Run for d in data]}"
                        raise RuntimeError(msg)

                verify_data(os_data)
                verify_data(es_data)

                """ Currently computing these via google sheets looks like:
                    base = (
                        f"{raw_sheet}!$E$2:$E=$A{index},"
                        f"{raw_sheet}!$G$2:$G<>0,"
                        f"{raw_sheet}!$H$2:$H=$C{index},"
                        f'{raw_sheet}!$I$2:$I="service_time"'
                    )
                    os_stat = f'{raw_sheet}!$C$2:$C="OS",' f'{raw_sheet}!$D$2:$D="{os}",' + base
                    cell_os_p50_stdev = f"G{index}"
                    cell_os_p90_stdev = f"H{index}"
                    cell_os_p50_avg = f"I{index}"
                    cell_os_p90_avg = f"J{index}"

                    f"=STDEV.S(FILTER({raw_sheet}!$J$2:$J, {os_stat}))",  # p50 stdev
                    f"={cell_es_p50_stdev}/{cell_es_p50_avg}",  # p50 rsd
                """
                os_std_50 = stdev(float(row.P50) for row in os_data)
                os_std_90 = stdev(float(row.P90) for row in os_data)
                os_avg_50 = mean(float(row.P50) for row in os_data)
                os_avg_90 = mean(float(row.P90) for row in os_data)
                os_rsd_50 = os_std_50 / os_avg_50
                os_rsd_90 = os_std_90 / os_avg_90

                es_std_50 = stdev(float(row.P50) for row in es_data)
                es_std_90 = stdev(float(row.P90) for row in es_data)
                es_avg_50 = mean(float(row.P50) for row in es_data)
                es_avg_90 = mean(float(row.P90) for row in es_data)
                es_rsd_50 = es_std_50 / es_avg_50
                es_rsd_90 = es_std_90 / es_avg_90

                comparison = es_avg_90 / os_avg_90
                results.append(
                    Result(
                        workload=workload,
                        category=category,
                        operation=operation,
                        os_version=compare.os_version,
                        os_std_50=os_std_50,
                        os_std_90=os_std_90,
                        os_avg_50=os_avg_50,
                        os_avg_90=os_avg_90,
                        os_rsd_50=os_rsd_50,
                        os_rsd_90=os_rsd_90,
                        es_version=compare.es_version,
                        es_std_50=es_std_50,
                        es_std_90=es_std_90,
                        es_avg_50=es_avg_50,
                        es_avg_90=es_avg_90,
                        es_rsd_50=es_rsd_50,
                        es_rsd_90=es_rsd_90,
                        comparison=comparison,
                    )
                )
    return results


class SheetsAPI:
    # TODO: wrap requests to check rate limit
    service = Resource
    spreadsheet_id: str

    def __init__(self, token: Path, credentials: Path | None = None):
        raise NotImplementedError

    def create_sheet(self, sheet_name: str) -> None:
        raise NotImplementedError

    def insert_rows(self, sheet_name: str, sheet_range: str, rows: list[list[str]]) -> None:
        request_properties: dict = {
            "majorDimension": "ROWS",
            "values": rows,
        }
        self.service.spreadsheets().values().append(
            spreadsheetId=self.spreadsheet_id,
            range=f"{sheet_name}!{sheet_range}",
            valueInputOption="USER_ENTERED",
            body=request_properties,
        ).execute()
        raise NotImplementedError


def create_google_sheet(data: list[Result]) -> None:
    sheets_api = SheetsAPI(Path("./token.json"))

    header = [
        [
            "Workload",
            "Category",
            "Operation",
            "Comparison\nES/OS",
            "",
            "OS Version",
            "OS: STDEV 50",
            "OS: STDEV 90",
            "OS: AVG 50",
            "OS: AVG 90",
            "OS: RSD 50",
            "OS: RSD 90",
            "",
            "ES Version",
            "ES: STDEV 50",
            "ES: STDEV 90",
            "ES: AVG 50",
            "ES: AVG 90",
            "ES: RSD 50",
            "ES: RSD 90",
        ]
    ]
    sheet_rows = header + [
        [
            row.workload,
            row.category,
            row.operation,
            str(row.comparison),
            "",
            row.os_version,
            str(row.os_std_50),
            str(row.os_std_90),
            str(row.os_avg_50),
            str(row.os_avg_90),
            str(row.os_rsd_50),
            str(row.os_rsd_90),
            "",
            row.os_version,
            str(row.os_std_50),
            str(row.os_std_90),
            str(row.os_avg_50),
            str(row.os_avg_90),
            str(row.os_rsd_50),
            str(row.os_rsd_90),
        ]
        for row in data
    ]

    results_sheet_name = "Results"

    sheets_api.create_sheet(results_sheet_name)
    sheets_api.insert_rows(results_sheet_name, "A1", sheet_rows)

    # TODO: sheets formatting api calls as before


def stats_comparing(results: list[Result]) -> None:
    """Rough example of what computing the  Statistics comparing summary table could look like."""
    os_faster = [row.comparison for row in results if row.comparison > 1]
    os_slower = [row.comparison for row in results if row.comparison < 1]

    def stats(rows: list[float]) -> None:
        """Just an example of computing additional stats."""
        print(f"Average: {mean(rows)}")
        print(f"Median: {median(rows)}")
        print(f"Max: {max(rows)}")
        print(f"StdDev: {stdev(rows)}")
        print(f"Variance: {variance(rows)}")

    stats(os_faster)
    stats(os_slower)
