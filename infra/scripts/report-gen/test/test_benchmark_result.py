"""Test BenchmarkResult serialization and deserialization."""

from pathlib import Path
from tempfile import TemporaryDirectory

from report_gen.download import dump_csv_files, read_csv_files


def test_benchmark_serialization() -> None:
    test_data = Path("test/data/test_data")

    expected_results = read_csv_files(test_data)

    with TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        dump_csv_files(expected_results, tmp_path)
        actual_results = read_csv_files(tmp_path)
    assert len(actual_results) == len(expected_results), "Mismatch in number of results"

    for i, (actual, expected) in enumerate(zip(actual_results, expected_results, strict=True)):
        assert actual == expected, f"{i} {actual=} {expected=}"
