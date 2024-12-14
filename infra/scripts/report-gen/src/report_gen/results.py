"""Calculate Results."""

from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from statistics import mean, median, stdev, variance

from .download import BenchmarkResult
from .google_sheets import SheetsBuilder
from .sheets.common import get_category


@dataclass
class VersionPair:
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

    @property
    def relative_diff(self) -> float:
        """(ES-OS) / AVG(ES,OS)."""
        es = self.es_avg_90
        os = self.os_avg_90
        return (es - os) / mean([es, os])

    @property
    def ratio(self) -> float:
        """ES / OS."""
        return self.es_avg_90 / self.os_avg_90


def build_results(data: list[BenchmarkResult], comparisons: list[VersionPair]) -> list[Result]:  # noqa: C901
    """Build the results data from the raw benchmark results."""
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
        for operation, rows in operations.items():
            category = get_category(workload, operation)

            os_rows = [row for row in rows if row.Engine == "OS"]
            es_rows = [row for row in rows if row.Engine == "ES"]
            for compare in comparisons:
                os_data = [row for row in os_rows if row.EngineVersion == compare.os_version]
                if len(os_data) == 0:
                    raise RuntimeError(f"No data for OS {compare.os_version}")  # noqa: TRY003, EM102
                es_data = [row for row in es_rows if row.EngineVersion == compare.es_version]
                if len(es_data) == 0:
                    raise RuntimeError(f"No data for OS {compare.es_version}")  # noqa: TRY003, EM102

                def verify_data(engine: str, workload: str, operation: str, data: list[BenchmarkResult]) -> None:
                    """Check assumptions about the data before reporting stats."""
                    runs = defaultdict(set)
                    for d in data:
                        runs[d.RunGroup].add(d.Run)
                    # We expect each run group to have 4 data points
                    # Technically 5 but we disregard run 0
                    for group, run_counts in runs.items():
                        if run_counts != {"1", "2", "3", "4"}:
                            msg = f"{engine}-{workload}-{operation} {group} expected 4 runs but got {run_counts}"
                            raise RuntimeError(msg)

                verify_data("OS", workload, operation, os_data)
                verify_data("ES", workload, operation, es_data)

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


class EngineTable:
    """Table showing the number of tests run for each Engine/Version/Workload combo."""

    @dataclass
    class Row:
        """Single Row in the Engine Table."""

        engine: str
        version: str
        workload: str
        test_count: int

    rows: list[Row]

    def __init__(self, results: list[BenchmarkResult]) -> None:
        # Sort the results by Engine/Version/Workload to be counted
        filtered: dict[tuple[str, str, str], list[BenchmarkResult]] = defaultdict(list)

        for r in results:
            key = (r.Engine, r.EngineVersion, r.Workload)
            filtered[key].append(r)

        self.rows = [
            EngineTable.Row(
                engine=grouped_results[0].Engine,
                version=grouped_results[0].EngineVersion,
                workload=grouped_results[0].Workload,
                test_count=len(grouped_results),
            )
            for grouped_results in filtered.values()
        ]


def create_google_sheet(data: list[Result], token: Path, credentials: Path | None = None) -> None:
    """Export data to a google sheet."""
    sheets_api = SheetsBuilder("Report", token, credentials)

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

    nrows = len(sheet_rows)

    results_sheet_name = "Results"
    sheets_api.create_sheet(results_sheet_name)
    sheets_api.insert_rows(results_sheet_name, "A1", sheet_rows)
    fmt = sheets_api.format_builder(results_sheet_name)
    fmt.bold_font("A1:T1")
    fmt.freeze_row(1)
    fmt.freeze_col(4)
    for r in [f"D2:D{nrows}", f"G2:G{nrows}", f"O2:T{nrows}"]:
        fmt.style_float(r)
    fmt.color_comparison(f"D2:D{nrows}")
    fmt.rsd(f"K2:L{nrows}")
    fmt.rsd(f"S2:T{nrows}")
    fmt.apply()


def stats_comparing(results: list[Result]) -> None:
    """Rough example of what computing the  Statistics comparing summary table could look like."""
    os_faster = [row.comparison for row in results if row.comparison > 1]
    os_slower = [row.comparison for row in results if row.comparison < 1]

    def stats(rows: list[float]) -> None:
        """Just an example of computing additional stats."""
        _a = f"Average: {mean(rows)}"
        _b = f"Median: {median(rows)}"
        _c = f"Max: {max(rows)}"
        _d = f"StdDev: {stdev(rows)}"
        _e = f"Variance: {variance(rows)}"

    stats(os_faster)
    stats(os_slower)
