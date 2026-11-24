import pytest
from umbrella.choices import GRID_BOX_DEFAULTS

from cryo_grids.models import CryoGridBox
from cryo_grids.serializers import CryoGridBoxSerializer

pytestmark = pytest.mark.django_db


def _errors(data, instance=None):
    serializer = CryoGridBoxSerializer(instance, data=data, partial=instance is not None)
    serializer.is_valid()
    return serializer.errors


def test_create_accepts_supported_numbering():
    assert _errors({"name": "box", "max_grids": 8, "numbering": "col"}) == {}


def test_create_rejects_unsupported_numbering():
    assert "numbering" in _errors({"name": "box", "max_grids": 4, "numbering": "col"})


def test_create_rejects_six_grid_box():
    assert "max_grids" in _errors({"name": "box", "max_grids": 6, "numbering": "z"})


def test_legacy_combination_stays_editable():
    # 8-grid boxes were stored as "ucw" before per-size numbering existed.
    box = CryoGridBox.objects.create(name="legacy", max_grids=8, numbering="ucw")

    assert _errors({"name": "renamed", "numbering": "ucw"}, instance=box) == {}


def test_update_rejects_switch_to_unsupported_numbering():
    box = CryoGridBox.objects.create(name="box", max_grids=8, numbering="col")

    assert "numbering" in _errors({"numbering": "uccw"}, instance=box)


def test_choices_expose_grid_box_defaults(client, django_user_model):
    client.force_login(django_user_model.objects.create(username="choices-viewer"))

    response = client.get("/api/grid-logging/choices/")

    assert response.json()["grid_box_defaults"] == GRID_BOX_DEFAULTS
