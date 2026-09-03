"""resolve_defaults: schema < ParameterDefaults rows < session-derived values."""

import pytest
from processes.models import ParameterDefaults
from workflow.defaults import SOURCE_SCHEMA, SOURCE_SESSION, check_value_type, resolve_defaults
from workflow.processors.base import BaseProcessor

CZII = "czii"
BRUNO = "bruno"


class FakeProcessor(BaseProcessor):
    name = "test_processor"  # matches conftest test_proc_software.processor_class
    derived = {}

    def get_parameter_schema(self):
        return {
            "type": "object",
            "properties": {
                "binning": {"type": "integer", "default": 2},
                "mode": {"type": "string", "default": "fast", "enum": ["fast", "slow"]},
                "pixel_size": {"type": "number"},
                "verbose": {"type": "boolean", "default": False},
            },
            "required": ["pixel_size"],
        }

    def session_defaults(self, msi_session):
        return dict(self.derived)

    def render_script(self, params, run_context):
        return ""

    def validate_parameters(self, params):
        return []

    def on_job_submit(self, run_context, job_id):
        pass

    def on_job_complete(self, run_context, success):
        pass


@pytest.fixture
def processor():
    proc = FakeProcessor()
    proc.derived = {}
    return proc


def _row(software, values, **dims):
    return ParameterDefaults.objects.create(proc_software=software, values=values, **dims)


@pytest.mark.django_db
class TestResolveDefaults:
    def test_schema_only(self, processor, test_proc_software):
        resolved = resolve_defaults(processor)

        assert resolved.values == {"binning": 2, "mode": "fast", "verbose": False}
        assert resolved.required == set()
        assert set(resolved.sources.values()) == {SOURCE_SCHEMA}

    def test_no_proc_software_row_means_schema_only(self, processor, db):
        assert resolve_defaults(processor).values == {"binning": 2, "mode": "fast", "verbose": False}

    def test_row_overrides_schema(self, processor, test_proc_software):
        row = _row(test_proc_software, {"binning": 4})

        resolved = resolve_defaults(processor)

        assert resolved.values["binning"] == 4
        assert resolved.sources["binning"] == "row:%d" % row.pk

    def test_specific_row_beats_general(self, processor, test_proc_software, test_msi_session):
        _row(test_proc_software, {"binning": 4})
        _row(test_proc_software, {"binning": 8}, scope=test_msi_session.session_plan.scope)

        assert resolve_defaults(processor, msi_session=test_msi_session).values["binning"] == 8

    def test_scope_row_ignored_without_session(self, processor, test_proc_software, test_session_plan):
        _row(test_proc_software, {"binning": 8}, scope=test_session_plan.scope)

        assert resolve_defaults(processor).values["binning"] == 2

    def test_null_clears_and_requires(self, processor, test_proc_software):
        _row(test_proc_software, {"mode": None})

        resolved = resolve_defaults(processor)

        assert "mode" not in resolved.values
        assert resolved.required == {"mode"}

    def test_session_value_beats_row_null(self, processor, test_proc_software, test_msi_session):
        _row(test_proc_software, {"binning": None})
        processor.derived = {"binning": 1, "pixel_size": 1.9}

        resolved = resolve_defaults(processor, msi_session=test_msi_session)

        assert resolved.values["binning"] == 1
        assert resolved.values["pixel_size"] == 1.9
        assert resolved.required == set()
        assert resolved.sources["pixel_size"] == SOURCE_SESSION

    def test_session_none_is_ignored(self, processor, test_proc_software, test_msi_session):
        processor.derived = {"pixel_size": None}

        assert "pixel_size" not in resolve_defaults(processor, msi_session=test_msi_session).values

    def test_cluster_defaults_to_software_default(self, processor, test_proc_software):
        from stores.models import Cluster

        _row(test_proc_software, {"binning": 6}, cluster=Cluster.objects.get(cluster_id=CZII))

        assert resolve_defaults(processor).values["binning"] == 6
        assert resolve_defaults(processor, cluster_id=BRUNO).values["binning"] == 2


class TestMergeAndMissing:
    def test_posted_wins_and_gaps_fill(self, processor, db):
        resolved = resolve_defaults(processor)

        assert resolved.merge({"binning": 9}) == {"binning": 9, "mode": "fast", "verbose": False}

    def test_missing_lists_schema_then_cleared_keys(self, processor, test_proc_software):
        _row(test_proc_software, {"mode": None})
        resolved = resolve_defaults(processor)

        merged = resolved.merge({"pixel_size": ""})

        assert resolved.missing(merged, ["pixel_size"]) == ["pixel_size", "mode"]
        assert resolved.missing(resolved.merge({"pixel_size": 1.0, "mode": "slow"}), ["pixel_size"]) == []


class TestCheckValueType:
    @pytest.mark.parametrize(
        "value, prop, error",
        [
            (None, {"type": "integer"}, None),
            (3, {"type": "integer"}, None),
            (True, {"type": "integer"}, "expected integer, got bool"),
            ("3", {"type": "integer"}, "expected integer, got str"),
            (3, {"type": "number"}, None),
            (2.5, {"type": "number"}, None),
            (False, {"type": "boolean"}, None),
            (0, {"type": "boolean"}, "expected boolean, got int"),
            ("slow", {"type": "string", "enum": ["fast", "slow"]}, None),
            ("warp", {"type": "string", "enum": ["fast", "slow"]}, "must be one of fast, slow"),
            ("x", {}, None),
        ],
    )
    def test_cases(self, value, prop, error):
        assert check_value_type(value, prop) == error
