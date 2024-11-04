"""Initial testing module."""

import report_gen


def test_version() -> None:
    version = getattr(report_gen, "__version__", None)
    assert version is not None
    assert isinstance(version, str)
