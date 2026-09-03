"""GET /workflow/v1/processors/<name>/defaults/ returns the resolved cascade."""

import pytest
from processes.models import ParameterDefaults
from workflow.processors import _PROCESSOR_REGISTRY
from workflow.processors.base import BaseProcessor

URL = "/workflow/v1/processors/test_processor/defaults/"


class EndpointProcessor(BaseProcessor):
    name = "test_processor"  # matches conftest test_proc_software.processor_class

    def get_parameter_schema(self):
        return {"type": "object", "properties": {"test_param": {"type": "integer"}, "other": {"type": "string"}}}

    def render_script(self, params, run_context):
        return ""

    def validate_parameters(self, params):
        return []

    def on_job_submit(self, run_context, job_id):
        pass

    def on_job_complete(self, run_context, success):
        pass


@pytest.fixture
def registered_processor():
    original = _PROCESSOR_REGISTRY.copy()
    _PROCESSOR_REGISTRY["test_processor"] = EndpointProcessor
    yield
    _PROCESSOR_REGISTRY.clear()
    _PROCESSOR_REGISTRY.update(original)


@pytest.mark.django_db
class TestProcessorDefaultsEndpoint:
    def test_shape_without_session(self, client, test_user, test_proc_software, registered_processor):
        client.force_login(test_user)

        data = client.get(URL).json()

        assert data == {
            "success": True,
            "defaults": {},
            "required_overrides": [],
            "sources": {},
            "session_info": {},
        }

    def test_row_and_cleared_key(self, client, test_user, test_proc_software, test_msi_session, registered_processor):
        client.force_login(test_user)
        row = ParameterDefaults.objects.create(
            proc_software=test_proc_software,
            scope=test_msi_session.session_plan.scope,
            values={"test_param": 42, "other": None},
        )

        data = client.get(URL, {"session_id": test_msi_session.name, "cluster": "czii"}).json()

        assert data["defaults"] == {"test_param": 42}
        assert data["required_overrides"] == ["other"]
        assert data["sources"] == {"test_param": "row:%d" % row.pk, "other": "row:%d" % row.pk}

    def test_unknown_processor_404(self, client, test_user):
        client.force_login(test_user)

        assert client.get("/workflow/v1/processors/nope/defaults/").status_code == 404
