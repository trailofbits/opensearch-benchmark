"""The `report-gen` entrypoint."""

import argparse
import logging
import os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from report_gen.diff import diff_folders
from report_gen.download import Source, download, dump_csv_files
from report_gen.sheets import create_report

from . import __version__
from .download import read_csv_files
from .results import create_google_sheet


def build_diff_args(diff_parser: argparse.ArgumentParser) -> None:
    def directory_path_parser(user_input: str) -> Path:
        if Path(user_input).is_dir():
            return Path(user_input)
        msg = f"Not a valid folder path: {user_input}"
        raise argparse.ArgumentTypeError(msg)

    diff_parser.add_argument(
        "--a",
        help="Path to the first benchmark data folder",
        required=True,
        type=directory_path_parser,
    )

    diff_parser.add_argument(
        "--b",
        help="Path to the second benchmark data folder",
        required=True,
        type=directory_path_parser,
    )


def diff_command(args: argparse.Namespace) -> None:
    folder_a: Path = args.a
    folder_b: Path = args.b
    diff_folders(folder_a, folder_b)


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
        help="Download results starting from this date (inclusive). " "Format is YYYY-MM-DD or YYYY-MM-DD hh:mm:ssZ",
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
        help="Which benchmark data run type (normally dev or official) to download " "(default: %(default)s)",
        type=str,
        choices=["official", "dev"],
        default="official",
    )
    download_parser.add_argument(
        "--environment",
        help="Which environment prefix to download (default: %(default)s)",
        type=str,
        default="",
    )
    download_parser.add_argument(
        "--engine-type",
        help="Which engine type to download (default: %(default)s)",
        type=str,
        default=None,
    )
    download_parser.add_argument(
        "--distribution-version",
        help="Which distribution version to download (default: %(default)s)",
        type=str,
        default=None,
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
        print("Datastore password missing, please pass it as the DS_PASSWORD environment variable")
        return

    benchmark_data_folder: Path = args.benchmark_data
    if not benchmark_data_folder.exists():
        print(f"Could not find the provided benchmark data folder at {benchmark_data_folder}")

    def validate_date(date_str: str) -> datetime:
        if "T" not in date_str:
            return datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=ZoneInfo("UTC"))
        return datetime.fromisoformat(date_str)

    try:
        start_date = validate_date(args.from_arg)
    except ValueError:
        print(
            "Wrong format for the 'from' parameter, " "please use a date in YYYY-MM-DD or YYYY-MM-DD hh:mm:ssZ format"
        )
        return

    if args.to_arg is None:
        end_date = datetime.now(tz=ZoneInfo("UTC"))
    else:
        try:
            end_date = validate_date(args.to_arg)
        except ValueError:
            print(
                "Wrong format for the 'to' parameter, " "please use a date in YYYY-MM-DD or YYYY-MM-DD hh:mm:ssZ format"
            )
            return

    if start_date > end_date:
        print("Wrong date range. The date in --from needs to be the same or before the one in --to")
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
        engine_type=args.engine_type,
        distribution_version=args.distribution_version,
        sources=sources,
    )

    dump_csv_files(benchmark_results, benchmark_data_folder)


def build_create_args(create_parser: argparse.ArgumentParser) -> None:
    def directory_path_parser(user_input: str) -> Path:
        if Path(user_input).is_dir():
            return Path(user_input)
        msg = f"Not a valid folder path: {user_input}"
        raise argparse.ArgumentTypeError(msg)

    def existing_file_path_parser(user_input: str) -> Path:
        if Path(user_input).is_file():
            return Path(user_input)
        msg = f"Not an existing file path: {user_input}"
        raise argparse.ArgumentTypeError(msg)

    create_parser.add_argument(
        "--credentials",
        help="Path to the credentials file",
        type=existing_file_path_parser,
        default=None,
    )

    create_parser.add_argument(
        "--token",
        help="Path to the token file." " If it's missing, use in combination with the --credentials parameter",
        required=True,
    )

    create_parser.add_argument(
        "--benchmark-data",
        help="Path to the benchmark data folder, which should contain the raw .csv files",
        required=True,
        type=directory_path_parser,
    )

    create_parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")


def create_command(args: argparse.Namespace) -> bool:
    benchmark_data = Path(args.benchmark_data)
    if not benchmark_data.is_dir():
        print(f"benchmark data '{benchmark_data}' is not a directory")
        return False
    token_path = Path(args.token)

    if args.credentials is None:
        credential_path = None
        if not token_path.is_file():
            print(f"token path '{token_path}' is not a file")
            return False
    else:
        credential_path = Path(args.credentials)
        if not credential_path.is_file():
            print(f"token path '{credential_path}' is not a file")
            return False

    return create_report(benchmark_data, token_path, credential_path) is not None


def main() -> None:
    logging.basicConfig(level=logging.INFO)

    bench_results = read_csv_files(Path("./download_nightly_2024-12-07_2024-12-14"))

    cred = Path("/Users/brad/Code/opensearch-benchmark/local/credentials.json")
    create_google_sheet(bench_results, Path("./token.json"), cred)

    return

    arg_parser = argparse.ArgumentParser(description="Tool to help download benchmark data and generate reports")
    subparser = arg_parser.add_subparsers(dest="command", help="Available Commands")

    download_parser = subparser.add_parser(
        "download",
        help="Downloads benchmark results from an OpenSearch datastore as CSVs "
        "with the format <run-group>-<engine>-<engine version>-<workload>-<test-procedure>.csv "
        "into a provided folder",
    )
    build_download_args(download_parser)

    create_parser = subparser.add_parser(
        "create",
        help="Creates a google sheet report from downloaded benchmark data",
    )
    build_create_args(create_parser)

    diff_parser = subparser.add_parser(
        "diff",
        help="Determines if two downloaded folders of CSV files are unusually different",
    )
    build_diff_args(diff_parser)

    args = arg_parser.parse_args()

    if args.command == "download":
        download_command(args)
    elif args.command == "create":
        create_command(args)
    elif args.command == "diff":
        diff_command(args)
