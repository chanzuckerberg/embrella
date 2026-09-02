"""natural_sort_key orders mixed human/machine naming without type errors;
msi_session_sort_key orders session names by date with the plan prefix as a tiebreak."""

import pytest

from common.sorting import SESSION_NAME_RE, msi_session_sort_key, natural_sort_key


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


class TestSessionNameRe:
    @pytest.mark.parametrize("name", ["26sep01a", "s26sep01a", "abcd26sep01a", "26sep01", "26sep01aa"])
    def test_matches_scheme(self, name):
        assert SESSION_NAME_RE.match(name)

    @pytest.mark.parametrize("name", ["S26sep01a", "26sep1a", "26SEP01a", "s26sep01a1", "", "invalid"])
    def test_rejects_off_scheme(self, name):
        assert not SESSION_NAME_RE.match(name)

    def test_groups(self):
        m = SESSION_NAME_RE.match("s26sep01b")
        assert (m["prefix"], m["yy"], m["mon"], m["dd"], m["seq"]) == ("s", "26", "sep", "01", "b")


class TestMsiSessionSortKey:
    def test_newest_first_and_prefix_only_breaks_ties(self):
        names = ["24jan01a", "s24jan01a", "26sep01a", "n26sep01a", "25may10b"]
        assert sorted(names, key=msi_session_sort_key) == [
            "26sep01a",
            "n26sep01a",
            "25may10b",
            "24jan01a",
            "s24jan01a",
        ]

    def test_seq_letters_order_within_a_day(self):
        names = ["26sep01c", "s26sep01a", "26sep01a", "26sep01b"]
        assert sorted(names, key=msi_session_sort_key) == ["26sep01a", "s26sep01a", "26sep01b", "26sep01c"]

    def test_missing_seq_reads_as_a(self):
        assert msi_session_sort_key("26sep01")[:4] == msi_session_sort_key("26sep01a")[:4]

    @pytest.mark.parametrize("name", ["invalid", "s24xyz01a", "24jan40a", "24jan00a", "", None])
    def test_unparseable_sorts_last(self, name):
        assert msi_session_sort_key(name) > msi_session_sort_key("00jan01z")
        assert msi_session_sort_key(name)[:4] == (0, 0, 0, "z")
