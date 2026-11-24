"""selected_positions over the two stored subset shapes, and CSV-text parsing."""

from pathlib import Path

import pytest

from depositions.services.subset import positions_from_csv_text, selected_positions

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.mark.parametrize(
    "stored,expected",
    [
        (None, []),
        ({}, []),
        (
            {"Selected positions": ["Position_1", " ", None, "Position_2"], "Filter type": "AND"},
            ["Position_1", "Position_2"],
        ),
        (
            [{"Tilt_Series": "Position_4.mrc"}, {"Tilt_Series": " "}, {"Tilt_Series": "Position_5"}],
            ["Position_4", "Position_5"],
        ),
    ],
)
def test_selected_positions(stored, expected):
    assert selected_positions(stored) == expected


@pytest.mark.parametrize(
    "text,expected",
    [
        ("Tilt_Series,Score\nPosition_1.mrc,0.9\nPosition_2,0.8\n", ["Position_1", "Position_2"]),
        ("\ufeffTilt_Series\nPosition_1\n", ["Position_1"]),  # Excel BOM on the header
        ("Score,Other\n1,2\n", []),  # no Tilt_Series column
    ],
)
def test_positions_from_csv_text(text, expected):
    assert positions_from_csv_text(text) == expected


def test_positions_from_example_csv_fixture():
    text = (FIXTURES / "subset_metrics.csv").read_text()
    assert positions_from_csv_text(text) == ["Position_1", "Position_2", "Position_3"]
