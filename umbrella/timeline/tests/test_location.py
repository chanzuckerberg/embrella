"""Unit tests for the stay-window helpers (no DB)."""

from datetime import UTC, datetime
from types import SimpleNamespace

from cryo_grids.history import ChangeReason

from timeline.sources.base import CHANGED, CREATED, DELETED
from timeline.sources.location import BEGINNING, Stay, clip, stays

# Spans years: grids can sit in one box for a long time
JAN_1_2024 = datetime(2024, 1, 1, tzinfo=UTC)
JAN_5_2024 = datetime(2024, 1, 5, tzinfo=UTC)
FEB_3_2026 = datetime(2026, 2, 3, tzinfo=UTC)
MAR_1_2026 = datetime(2026, 3, 1, tzinfo=UTC)


def row(at, box, kind=CHANGED, reason=None):
    return SimpleNamespace(history_date=at, box_id=box, history_type=kind, history_change_reason=reason)


class TestStays:
    def test_same_parent_merges(self):
        rows = [row(JAN_1_2024, 1, CREATED), row(JAN_5_2024, 1), row(FEB_3_2026, 2)]

        assert stays(rows, "box_id") == [Stay(1, JAN_1_2024, FEB_3_2026), Stay(2, FEB_3_2026)]

    def test_leaving_to_none_closes(self):
        rows = [row(JAN_1_2024, 1, CREATED), row(FEB_3_2026, None)]

        assert stays(rows, "box_id") == [Stay(1, JAN_1_2024, FEB_3_2026)]

    def test_delete_closes(self):
        rows = [row(JAN_1_2024, 1, CREATED), row(FEB_3_2026, 1, DELETED)]

        assert stays(rows, "box_id") == [Stay(1, JAN_1_2024, FEB_3_2026)]

    def test_baseline_starts_at_beginning(self):
        rows = [row(MAR_1_2026, 1, CREATED, ChangeReason.BASELINE)]

        assert stays(rows, "box_id") == [Stay(1, BEGINNING)]


class TestClip:
    def test_intersects(self):
        assert clip([Stay(7, BEGINNING, FEB_3_2026)], Stay(1, JAN_5_2024)) == [Stay(7, JAN_5_2024, FEB_3_2026)]

    def test_disjoint_dropped(self):
        assert clip([Stay(7, JAN_1_2024, JAN_5_2024)], Stay(1, FEB_3_2026, MAR_1_2026)) == []

    def test_open_ended(self):
        assert clip([Stay(7, JAN_1_2024)], Stay(1, JAN_5_2024)) == [Stay(7, JAN_5_2024)]


class TestHolds:
    def test_inside(self):
        assert Stay(1, JAN_1_2024, MAR_1_2026).holds(FEB_3_2026)

    def test_after_end(self):
        assert not Stay(1, JAN_1_2024, JAN_5_2024).holds(FEB_3_2026)
