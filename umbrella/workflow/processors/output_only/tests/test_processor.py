"""Output-only processors: registered and planned, hidden from launch, never rendered."""

import importlib

import pytest
from django.apps import apps
from processes.models import PipeInPlan, ProcPlan

from workflow.processors import get_processor, list_processors

PLANS = {
    "miss_alignment": ("czii-miss-alignment", "Miss-alignment refinement"),
    "isonet2": ("czii-isonet2", "IsoNet2"),
    "deepdewedge": ("czii-deepdewedge", "DeepDeWedge"),
    "icecream": ("czii-icecream", "ICECREAM"),
}

migration = importlib.import_module("processes.migrations.0053_init_output_only_procplans")


@pytest.mark.parametrize("name", PLANS)
def test_registered_and_hidden(name):
    processor = get_processor(name)

    assert name in list_processors()
    assert processor.hidden_from_list
    assert processor.display_name == PLANS[name][1]
    assert processor.get_database_metadata()["task_name"]


@pytest.mark.parametrize("name", PLANS)
def test_refuses_to_launch(name):
    processor = get_processor(name)

    assert processor.validate_parameters({}) == [processor._not_launchable()]
    with pytest.raises(NotImplementedError, match="cannot be launched"):
        processor.render_script({}, run_context=None)


@pytest.mark.django_db
def test_not_in_launch_list(logged_in_client):
    response = logged_in_client.get("/workflow/v1/processors/")

    assert response.status_code == 200
    listed = {processor["name"] for processor in response.json()["processors"]}
    assert listed.isdisjoint(PLANS)


@pytest.mark.django_db
@pytest.mark.parametrize("name", PLANS)
def test_migration_creates_plan(name):
    plan_name, display_name = PLANS[name]

    plan = ProcPlan.objects.get(name=plan_name)
    (step,) = PipeInPlan.objects.filter(plan=plan).select_related("pipe__software")

    assert plan.display_name == display_name
    assert step.pipe.software.processor_class == name
    assert step.pipe.software.name == name


@pytest.mark.django_db
@pytest.mark.parametrize("name", PLANS)
def test_processing_base_path_resolves(name):
    assert get_processor(name).get_processing_base_path().endswith(f"/{name}")


@pytest.mark.django_db
def test_migration_is_reversible():
    plan_names = [plan_name for plan_name, _ in PLANS.values()]

    migration.reverse_output_only_procplans(apps, None)
    assert not ProcPlan.objects.filter(name__in=plan_names).exists()

    migration.create_output_only_procplans(apps, None)
    assert ProcPlan.objects.filter(name__in=plan_names).count() == len(PLANS)
