"""Functions for merging cells."""


def format_merge(range_dict: dict) -> dict:
    """Merge range."""
    return {"mergeCells": {"range": range_dict, "mergeType": "MERGE_ALL"}}
