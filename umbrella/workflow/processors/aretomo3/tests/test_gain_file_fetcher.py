"""Gain listing: the pattern owns filtering, the {timestamp} group owns ordering, mtime is the fallback."""

from unittest.mock import patch

import pytest
from stores.models import FilePattern

from workflow.processors.aretomo3.gain_file_fetcher import ALL_FILES_GLOB, list_gain_files

GAIN_DIR = "/instrument/gain/"
CLUSTER = "c1"
LIST_FILES = "workflow.processors.aretomo3.gain_file_fetcher.list_files"

# krios1: several .gain files accumulate; the name carries the acquisition time.
FALCON_GAIN = FilePattern(list_glob="*.gain", regex=r"^(?P<timestamp>\d{8}_\d{6})_.+\.gain$")
# krios2: one .dm4 per session folder; nothing in the name to sort by.
K3_GAIN = FilePattern(list_glob="*.dm4", regex=r"^(?P<stem>.+)\.dm4$")


def entry(name, mtime, size=1):
    return {"name": name, "size_bytes": size, "modified_time": mtime, "full_path": GAIN_DIR + name}


def listing(*entries):
    return {"success": True, "files": list(entries), "error": None}


def names(result):
    return [f["filename"] for f in result["files"]]


class TestOrdering:
    def test_timestamp_group_beats_mtime(self):
        older_name_newer_mtime = entry("20250101_000000_EER_GainReference.gain", mtime=2_000_000_000)
        newer_name_older_mtime = entry("20251218_093959_EER_GainReference.gain", mtime=1_000_000_000)
        with patch(LIST_FILES, return_value=listing(older_name_newer_mtime, newer_name_older_mtime)):
            result = list_gain_files(GAIN_DIR, cluster_id=CLUSTER, file_pattern=FALCON_GAIN)

        assert names(result) == [
            "20251218_093959_EER_GainReference.gain",
            "20250101_000000_EER_GainReference.gain",
        ]

    def test_no_timestamp_group_falls_back_to_mtime(self):
        with patch(LIST_FILES, return_value=listing(entry("a.dm4", mtime=1), entry("b.dm4", mtime=2))):
            result = list_gain_files(GAIN_DIR, cluster_id=CLUSTER, file_pattern=K3_GAIN)
        assert names(result) == ["b.dm4", "a.dm4"]

    def test_no_pattern_lists_everything_by_mtime(self):
        with patch(LIST_FILES, return_value=listing(entry("x.bin", mtime=1), entry("y.gain", mtime=3))) as mock:
            result = list_gain_files(GAIN_DIR, cluster_id=CLUSTER)

        assert names(result) == ["y.gain", "x.bin"]
        mock.assert_called_once_with(GAIN_DIR, ALL_FILES_GLOB, cluster_id=CLUSTER)


class TestFiltering:
    def test_drops_non_matching_and_hidden(self):
        files = listing(
            entry("20251218_093959_EER_GainReference.gain", mtime=3),
            entry("notes.txt", mtime=2),
            entry(".20251219_000000_hidden.gain", mtime=4),
        )
        with patch(LIST_FILES, return_value=files):
            result = list_gain_files(GAIN_DIR, cluster_id=CLUSTER, file_pattern=FALCON_GAIN)
        assert names(result) == ["20251218_093959_EER_GainReference.gain"]

    def test_pattern_glob_and_cluster_reach_the_listing(self):
        with patch(LIST_FILES, return_value=listing()) as mock:
            list_gain_files(GAIN_DIR, cluster_id=CLUSTER, file_pattern=K3_GAIN)
        mock.assert_called_once_with(GAIN_DIR, "*.dm4", cluster_id=CLUSTER)


class TestResultShape:
    def test_formats_mtime_and_keeps_size(self):
        with patch(LIST_FILES, return_value=listing(entry("a.dm4", mtime=0, size=42))):
            result = list_gain_files(GAIN_DIR, cluster_id=CLUSTER, file_pattern=K3_GAIN)

        assert result["directory"] == GAIN_DIR
        assert result["files"] == [{"filename": "a.dm4", "modified_time": "1970-01-01 00:00:00", "size_bytes": 42}]

    @pytest.mark.parametrize("error", ["Parent directory does not exist: /instrument/gain", None])
    def test_listing_failure_passes_through(self, error):
        with patch(LIST_FILES, return_value={"success": False, "files": [], "error": error}):
            result = list_gain_files(GAIN_DIR, cluster_id=CLUSTER, file_pattern=FALCON_GAIN)

        assert result == {"success": False, "files": [], "directory": GAIN_DIR, "error": error}
