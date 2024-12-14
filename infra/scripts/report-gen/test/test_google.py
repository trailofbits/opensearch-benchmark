"""Test Google Sheets related functionality."""

from report_gen.google_sheets import convert_range_to_dict


def test_convert_range_to_dict() -> None:
    def exp(start_row: int, end_row: int, start_col: int, end_col: int) -> dict:
        return {
            "startRowIndex": start_row,
            "endRowIndex": end_row,
            "startColumnIndex": start_col,
            "endColumnIndex": end_col,
        }

    # Note the ranges are non-inclusive
    # So the end col and end row are 1 higher than the supplied row/col
    tests = [
        ("Sheet1!A5:D5", exp(start_row=4, end_row=5, start_col=0, end_col=4)),
        ("A5:D5", exp(start_row=4, end_row=5, start_col=0, end_col=4)),
        ("AA5:AB5", exp(start_row=4, end_row=5, start_col=26, end_col=28)),
        ("A1:A1", exp(start_row=0, end_row=1, start_col=0, end_col=1)),
    ]

    for test in tests:
        range_str = test[0]
        expected = test[1]
        actual = convert_range_to_dict(range_str)
        assert actual == expected, f"Input '{range_str}'. Expected '{expected}', Got '{actual}'"
