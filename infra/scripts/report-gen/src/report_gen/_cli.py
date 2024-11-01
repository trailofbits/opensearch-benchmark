"""The `report-gen` entrypoint."""

import argparse
import logging
import os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from report_gen.download import Source, download, dump_csv_files, say_download


def build_download_args(download_parser: argparse.ArgumentParser) -> None:
    download_parser.add_argument(
        "--host",
        help="Hostname of the datastore to download the benchmark results from",
        required=True,
        type=str,
    )
    download_parser.add_argument(
        "--port",
        help="Port of the datastore to download the benchmark results from (default: %(default)s)",
        type=int,
        default=443,
    )
    download_parser.add_argument(
        "--benchmark-data",
        help="Path to an existing folder to download the benchmark data to",
        type=Path,
        required=True,
    )
    download_parser.add_argument(
        "--from",
        help="Download results starting from this date (inclusive). "
        "Format is YYYY-MM-DD or YYYY-MM-DD hh:mm:ssZ",
        dest="from_arg",
        type=str,
        required=True,
    )
    download_parser.add_argument(
        "--to",
        help="Download results up to this date (inclusive). "
        "Format is YYYY-MM-DD or YYYY-MM-DD hh:mm:ssZ. Default is now",
        dest="to_arg",
        type=str,
        default=None,
    )
    download_parser.add_argument(
        "--run-type",
        help="Which benchmark data run type (normally dev or official) to download "
        "(default: %(default)s)",
        type=str,
        default="official",
    )
    download_parser.add_argument(
        "--environment",
        help="Which environment prefix to download (default: %(default)s)",
        type=str,
        default="",
    )
    download_parser.add_argument(
        "--source",
        metavar="SOURCE",
        help="Space separated list of sources of the benchmark results. "
        "Can be any combination of ['ci-scheduled', 'ci-manual', 'other'] (default: %(default)s)",
        nargs="+",
        choices=["ci-scheduled", "ci-manual", "other"],
        default=["ci-scheduled"],
    )


def download_command(args: argparse.Namespace) -> None:
    password = os.environ.get("DS_PASSWORD")
    if password is None:
        print(
            "Datastore password missing, please pass it as the DS_PASSWORD environment variable"
        )
        return

    benchmark_data_folder: Path = args.benchmark_data
    if not benchmark_data_folder.exists():
        print(
            f"Could not find the provided benchmark data folder at {benchmark_data_folder}"
        )

    def validate_date(date_str: str) -> datetime:
        if "T" not in date_str:
            return datetime.strptime(date_str, "%Y-%m-%d").replace(
                tzinfo=ZoneInfo("UTC")
            )
        return datetime.fromisoformat(date_str)

    try:
        start_date = validate_date(args.from_arg)
    except ValueError:
        print(
            "Wrong format for the 'from' parameter, "
            "please use a date in YYYY-MM-DD or YYYY-MM-DD hh:mm:ssZ format"
        )
        return

    if args.to_arg is None:
        end_date = datetime.now(tz=ZoneInfo("UTC"))
    else:
        try:
            end_date = validate_date(args.to_arg)
        except ValueError:
            print(
                "Wrong format for the 'to' parameter, "
                "please use a date in YYYY-MM-DD or YYYY-MM-DD hh:mm:ssZ format"
            )
            return

    if start_date > end_date:
        print(
            "Wrong date range. The date in --from needs to be the same or before the one in --to"
        )
        return

    src_map = {
        "ci-scheduled": Source.Scheduled,
        "ci-manual": Source.Manual,
        "other": Source.Other,
    }
    sources = [src_map[s] for s in args.source]

    benchmark_results = download(
        start_date=start_date,
        end_date=end_date,
        host=args.host,
        port=args.port,
        password=password,
        environment=args.environment,
        run_type=args.run_type,
        sources=sources,
    )

    dump_csv_files(benchmark_results, benchmark_data_folder)


def main() -> None:
    arg_parser = argparse.ArgumentParser(
        description="Tool to help download benchmark data and generate reports"
    )
    subparser = arg_parser.add_subparsers(dest="command", help="Available Commands")

    download_parser = subparser.add_parser(
        "download",
        help="Downloads benchmark results from an OpenSearch datastore as CSVs "
        "with the format <run-group>-<engine>-<engine version>-<workload>-<test-procedure>.csv "
        "into a provided folder",
    )
    build_download_args(download_parser)

    args = arg_parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    if args.command == "download":
        download_command(args)
