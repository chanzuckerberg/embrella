"""Reading the attempt-tagged pre-flight result from the prep log, and the push gate."""

import json

import pytest

from depositions.services.validation import MARKER, result_for_attempt


def _passed(attempt="42", dataset_id=7):
    return {"status": "passed", "attempt": attempt, "dataset_id": dataset_id, "warnings": [], "blocking_issues": []}


def _line(result):
    return MARKER + json.dumps(result)


def test_reads_matching_result():
    out = f"sync chatter\n{_line(_passed())}\n"
    assert result_for_attempt(out, "42", 7)["status"] == "passed"


def test_takes_the_last_marker_line():
    stale = {**_passed(), "status": "failed", "blocking_issues": [{"message": "old"}]}
    out = f"{_line(stale)}\n{_line(_passed())}\n"
    assert result_for_attempt(out, "42", 7)["status"] == "passed"


@pytest.mark.parametrize(
    "output",
    [
        _line(_passed(attempt="99")),  # wrong attempt
        _line(_passed(dataset_id=99)),  # wrong dataset
        _line({**_passed(), "status": "weird"}),  # unknown status
        _line({**_passed(), "blocking_issues": [{"message": "x"}]}),  # passed with blocking issues
        _line({**_passed(), "status": "failed", "warnings": [{"message": "x"}] * 21}),  # oversized list
        _line({**_passed(), "status": "failed", "blocking_issues": [{"oops": 1}]}),  # item without a message
        "just logs",  # no marker
        MARKER + "not json",  # unparseable
        "",  # empty
    ],
)
def test_bad_result_falls_back_to_unavailable(output):
    assert result_for_attempt(output, "42", 7)["status"] == "unavailable"
