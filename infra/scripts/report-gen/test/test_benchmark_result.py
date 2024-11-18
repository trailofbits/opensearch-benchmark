"""Test BenchmarkResult serialization and deserialization."""

from report_gen.download import read_csv_files, dump_csv_files

from pathlib import Path

from tempfile import TemporaryDirectory


def test_benchmark_serialization() -> None:
    test_data = Path("test/data/test_data")

    expected_results = read_csv_files(test_data)

    with TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        dump_csv_files(expected_results, tmp_path)
        actual_results = read_csv_files(tmp_path)
    assert len(actual_results) == len(expected_results), "Mismatch in number of results"

    for actual, expected in zip(actual_results, expected_results, strict=True):
        assert actual == expected
