"""The seeded deposition_staging path (migration 0027)."""

import pytest

from stores.paths import UnresolvedPlaceholderError, resolve_dir
from stores.placeholders import known_placeholders

pytestmark = pytest.mark.django_db


def test_deposition_id_is_a_known_placeholder():
    assert "deposition_id" in known_placeholders()


def test_resolves_the_seeded_staging_path():
    assert resolve_dir("deposition_staging", deposition_id=123) == "/hpc/projects/group.czii/depositions/123/"


def test_requires_deposition_id():
    with pytest.raises(UnresolvedPlaceholderError):
        resolve_dir("deposition_staging")
