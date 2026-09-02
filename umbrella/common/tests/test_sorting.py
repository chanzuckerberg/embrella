"""natural_sort_key orders mixed human/machine naming without type errors."""

from common.sorting import natural_sort_key


def test_numeric_runs_compare_numerically():
    names = ["Position_10_2", "Position_2", "Position_10"]
    assert sorted(names, key=natural_sort_key) == ["Position_2", "Position_10", "Position_10_2"]


def test_new_scope_stems_sort_naturally():
    names = ["pt729_ts_002", "pt712_ts_001", "pt729_ts_001"]
    assert sorted(names, key=natural_sort_key) == ["pt712_ts_001", "pt729_ts_001", "pt729_ts_002"]


def test_mixed_shapes_do_not_raise():
    """The old review-API key mixed lists and float('inf'), a TypeError when both appeared."""
    names = ["pt712_ts_001", "Position_2", "12x", "Position_10"]
    assert sorted(names, key=natural_sort_key) == ["12x", "Position_2", "Position_10", "pt712_ts_001"]


def test_missing_sorts_last():
    names = ["None", "Position_1", None]
    assert sorted(names, key=natural_sort_key) == ["Position_1", "None", None]
