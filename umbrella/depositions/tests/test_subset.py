"""selected_positions over the two stored subset shapes."""

import pytest

from depositions.services.subset import selected_positions


@pytest.mark.parametrize(
    "stored,expected",
    [
        (None, []),
        ({}, []),
        ({"Selected positions": ["Position_1", "Position_2"], "Filter type": "AND"}, ["Position_1", "Position_2"]),
        ([{"Tilt_Series": "Position_4.mrc"}, {"Tilt_Series": "Position_5"}], ["Position_4", "Position_5"]),
    ],
)
def test_selected_positions(stored, expected):
    assert selected_positions(stored) == expected
