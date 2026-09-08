"""ParameterDefaults: which rows apply to a launch, and in what order."""

import pytest
from django.core.exceptions import ValidationError
from stores.models import Cluster
from tem.models import Microscope, Software

from processes.models import ParameterDefaults, ProcSoftware

CZII = "czii"
BRUNO = "bruno"


@pytest.fixture
def proc_software(db):
    return ProcSoftware.objects.create(name="aretomo3", processor_class="aretomo3")


@pytest.fixture
def czii(db):
    return Cluster.objects.get(cluster_id=CZII)


def _row(proc_software, **dims):
    return ParameterDefaults.objects.create(proc_software=proc_software, values={}, **dims)


def _dims(plan):
    return {"software_id": plan.software_id, "scope_id": plan.scope_id}


class TestSpecificity:
    def test_bit_order_software_scope_cluster(self, proc_software, session_plan, czii):
        assert _row(proc_software).specificity == 0b000
        assert _row(proc_software, software=session_plan.software).specificity == 0b001
        assert _row(proc_software, scope=session_plan.scope).specificity == 0b010
        assert _row(proc_software, cluster=czii).specificity == 0b100

    def test_applicable_orders_all_eight_masks(self, proc_software, session_plan, czii):
        sw, sc = session_plan.software, session_plan.scope
        combos = [
            {},
            {"software": sw},
            {"scope": sc},
            {"software": sw, "scope": sc},
            {"cluster": czii},
            {"software": sw, "cluster": czii},
            {"scope": sc, "cluster": czii},
            {"software": sw, "scope": sc, "cluster": czii},
        ]
        # Create in reverse so pk order can't be what sorts them.
        for dims in reversed(combos):
            _row(proc_software, **dims)

        rows = ParameterDefaults.applicable(proc_software, **_dims(session_plan), cluster_id=CZII)

        assert [row.specificity for row in rows] == list(range(8))


class TestApplicable:
    def test_without_plan_only_dimensionless_rows(self, proc_software, session_plan, czii):
        any_row = _row(proc_software)
        _row(proc_software, software=session_plan.software)
        _row(proc_software, scope=session_plan.scope)
        _row(proc_software, cluster=czii)

        assert ParameterDefaults.applicable(proc_software) == [any_row]

    def test_cluster_without_plan(self, proc_software, session_plan, czii):
        any_row = _row(proc_software)
        cluster_row = _row(proc_software, cluster=czii)
        _row(proc_software, scope=session_plan.scope)

        assert ParameterDefaults.applicable(proc_software, cluster_id=CZII) == [any_row, cluster_row]

    def test_other_scope_software_cluster_excluded(self, proc_software, session_plan, czii):
        matching = _row(proc_software, scope=session_plan.scope)
        _row(proc_software, scope=Microscope.objects.create(name="OtherScope", cs=2.7))
        _row(proc_software, software=Software.objects.create(name="OtherSoftware"))
        _row(proc_software, cluster=Cluster.objects.get(cluster_id=BRUNO))

        assert ParameterDefaults.applicable(proc_software, **_dims(session_plan), cluster_id=CZII) == [matching]

    def test_exclude_pk_drops_that_row(self, proc_software, session_plan):
        any_row = _row(proc_software)
        scope_row = _row(proc_software, scope=session_plan.scope)

        rows = ParameterDefaults.applicable(proc_software, **_dims(session_plan), exclude_pk=scope_row.pk)

        assert rows == [any_row]

    def test_inactive_and_other_processor_excluded(self, proc_software, session_plan):
        _row(proc_software, is_active=False)
        other = ProcSoftware.objects.create(name="denoise", processor_class="denoiset")
        _row(other)

        assert ParameterDefaults.applicable(proc_software, **_dims(session_plan)) == []


class TestClean:
    def test_values_must_be_object(self, proc_software):
        row = ParameterDefaults(proc_software=proc_software, values=[1, 2])

        with pytest.raises(ValidationError) as exc:
            row.clean()

        assert "values" in exc.value.message_dict

    def test_duplicate_dimensions_rejected(self, proc_software, session_plan):
        _row(proc_software, scope=session_plan.scope)
        twin = ParameterDefaults(proc_software=proc_software, scope=session_plan.scope, values={})

        with pytest.raises(ValidationError):
            twin.clean()

    def test_existing_row_is_not_its_own_twin(self, proc_software, session_plan):
        row = _row(proc_software, scope=session_plan.scope)

        row.clean()

    def test_inactive_twin_allowed(self, proc_software, session_plan):
        _row(proc_software, scope=session_plan.scope, is_active=False)
        row = ParameterDefaults(proc_software=proc_software, scope=session_plan.scope, values={})

        row.clean()
