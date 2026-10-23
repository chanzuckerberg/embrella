"""
Tests for Generic Pipeline Execution Infrastructure

Tests the processor registry, execution engine, and API endpoints.
"""

from unittest.mock import MagicMock, patch

import pytest
from processes.models import PipeExecution
from workflow.execution import PipelineExecutor, RunContext, ValidationError
from workflow.processors import get_processor, register_processor
from workflow.processors.base import BaseProcessor
from workflow.processors.copick import CopickProcessor
from workflow.processors.denoiset import DenoisETProcessor

# Test Fixtures


@pytest.fixture
def test_processor_class():
    """Create a test processor class."""

    class TestProcessor(BaseProcessor):
        name = "test_processor"
        display_name = "Test Processor"
        version = "1.0.0"

        def get_parameter_schema(self):
            return {
                "type": "object",
                "properties": {
                    "test_param": {
                        "type": "number",
                        "title": "Test Parameter",
                        "minimum": 0,
                        "maximum": 100,
                    },
                },
                "required": ["test_param"],
            }

        def render_script(self, params, run_context):
            return f"#!/bin/bash\necho {params['test_param']}"

        def on_job_submit(self, run_context, job_id):
            """Hook called after successful job submission."""
            pass

        def on_job_complete(self, run_context, success):
            """Hook called when job completes."""
            pass

        def validate_parameters(self, params):
            errors = []
            if params.get("test_param", 0) < 0:
                errors.append("test_param must be non-negative")
            return errors

    return TestProcessor


@pytest.fixture
def registered_test_processor(test_processor_class):
    """Register the test processor and clean up after test."""
    from workflow.processors import _PROCESSOR_REGISTRY

    # Register
    original_registry = _PROCESSOR_REGISTRY.copy()
    _PROCESSOR_REGISTRY["test_processor"] = test_processor_class

    yield test_processor_class

    # Cleanup - restore original registry
    _PROCESSOR_REGISTRY.clear()
    _PROCESSOR_REGISTRY.update(original_registry)


def _bare_context(inputs):
    """RunContext without DB rows, for logic that only reads inputs."""
    return RunContext(
        proc_run=None,
        pipe_in_plan=None,
        msi_session=None,
        user=None,
        cluster_id="czii",
        run_number="run001",
        job_name="test_job_name",
        inputs=inputs,
    )


# Processor Registry Tests


class TestProcessorRegistry:
    """Tests for the processor registry system."""

    def test_register_duplicate_name_fails(self, registered_test_processor):
        """A second class claiming a registered name is rejected, not silently swapped in."""

        class Impostor(BaseProcessor):
            name = "test_processor"

        with pytest.raises(ValueError, match="already registered"):
            register_processor(Impostor)

    def test_register_processor_without_name_fails(self):
        """Test that registering a processor without a name fails."""

        class BadProcessor(BaseProcessor):
            # Missing name attribute
            pass

        with pytest.raises(ValueError, match="must define a 'name' class attribute"):
            register_processor(BadProcessor)

    def test_get_nonexistent_processor_fails(self):
        """Test that getting a non-existent processor raises ValueError."""
        with pytest.raises(ValueError, match="Unknown processor"):
            get_processor("nonexistent")


# RunContext Tests


class TestRunContext:
    """Tests for RunContext data structure."""

    def test_get_placeholder_map(self, test_proc_run, test_pipe_in_plan, test_msi_session, test_user):
        """The placeholder map is the contract processors resolve DB templates against."""
        context = RunContext(
            proc_run=test_proc_run,
            pipe_in_plan=test_pipe_in_plan,
            msi_session=test_msi_session,
            user=test_user,
            cluster_id="czii",
            run_number="run001",
            job_name="test_job_name",
            inputs={},
        )

        placeholders = context.get_placeholder_map()

        assert placeholders["scope"] == "TestScope"
        assert placeholders["msi_session"] == "24nov10"
        assert placeholders["proc_software"] == "test_software"
        assert placeholders["proc_run"] == "run001"
        assert placeholders["pipe"] == "test_pipe"
        assert placeholders["proc_plan"] == "test_plan"
        # {workflow} is the legacy alias of {proc_software} in this lane.
        assert placeholders["workflow"] == placeholders["proc_software"]

    @pytest.mark.parametrize(
        "inputs, required, expected",
        [
            ({"aln": "/path/to/alignment.txt"}, True, "/path/to/alignment.txt"),
            ({}, False, None),
        ],
    )
    def test_get_input(self, inputs, required, expected):
        assert _bare_context(inputs).get_input("aln", required=required) == expected

    def test_get_input_missing_required_fails(self):
        with pytest.raises(ValueError, match="Required input 'aln' not found"):
            _bare_context({}).get_input("aln", required=True)


# PipelineExecutor Tests


class TestPipelineExecutor:
    """Tests for PipelineExecutor."""

    @patch("processes.tasks.start_job_status_syncer")
    @patch("workflow.execution.RemoteJobSubmitter")
    def test_execute_pipe(
        self,
        mock_submitter_class,
        mock_start_syncer,
        test_proc_run,
        test_pipe_in_plan,
        test_user,
        registered_test_processor,
    ):
        """Test executing a pipe."""
        # Mock the RemoteJobSubmitter
        mock_submitter = MagicMock()
        mock_submitter.run_script.return_value = ("Submitted batch job 123456", "")
        mock_submitter.last_script_path = "/scripts/test_script.sh"
        mock_submitter_class.return_value = mock_submitter

        executor = PipelineExecutor()

        result = executor.execute_pipe(
            pipe_in_plan=test_pipe_in_plan,
            proc_run=test_proc_run,
            user=test_user,
            parameters={"test_param": 50},
            auth={"username": "test", "password": "pass"},
        )

        assert result["job_id"] == "123456"
        assert result["status"] == "submitted"
        assert "pipe_execution_id" in result

        # Verify PipeExecution was created
        execution = PipeExecution.objects.get(id=result["pipe_execution_id"])
        assert execution.proc_run == test_proc_run
        assert execution.pipe_in_plan == test_pipe_in_plan
        assert execution.status == "submitted"
        assert execution.job_id == "123456"
        # Executor also stamps cluster_id and the resolved paths on parameters for
        # downstream tracking.
        assert execution.parameters == {
            "test_param": 50,
            "cluster_id": "czii",
            "_paths_used": {
                "processing_base_path": "/hpc/projects/group.czii/krios1.processing/test_software",
                "output_patterns": {},
            },
        }
        # PipeExecution status is owned by the sacct syncer alone
        mock_start_syncer.assert_called_once_with(job_id="123456", cluster_id="czii")

    @patch("workflow.execution.RemoteJobSubmitter")
    def test_execute_pipe_stamps_bruno_cluster_id(
        self,
        mock_submitter_class,
        test_proc_run,
        test_pipe_in_plan,
        test_user,
        registered_test_processor,
    ):
        """Executing on a non-default cluster stamps the chosen cluster_id on parameters."""
        mock_submitter = MagicMock()
        mock_submitter.run_script.return_value = ("Submitted batch job 654321", "")
        mock_submitter.last_script_path = "/scripts/test_script.sh"
        mock_submitter_class.return_value = mock_submitter

        executor = PipelineExecutor()

        result = executor.execute_pipe(
            pipe_in_plan=test_pipe_in_plan,
            proc_run=test_proc_run,
            user=test_user,
            parameters={"test_param": 10},
            auth={"username": "test", "password": "pass"},
            cluster_id="bruno",
        )

        # RemoteJobSubmitter was constructed for the bruno cluster.
        assert mock_submitter_class.call_args.kwargs["cluster_id"] == "bruno"

        # PipeExecution.parameters carries cluster_id=bruno for the syncer/metadata views.
        execution = PipeExecution.objects.get(id=result["pipe_execution_id"])
        assert execution.parameters["cluster_id"] == "bruno"

    def test_execute_pipe_validation_fails(
        self,
        test_proc_run,
        test_pipe_in_plan,
        test_user,
        registered_test_processor,
    ):
        """Test that invalid parameters fail validation."""
        executor = PipelineExecutor()

        with pytest.raises(ValidationError) as exc_info:
            executor.execute_pipe(
                pipe_in_plan=test_pipe_in_plan,
                proc_run=test_proc_run,
                user=test_user,
                parameters={"test_param": -10},  # Invalid - negative
                auth={"username": "test", "password": "pass"},
            )

        assert "test_param must be non-negative" in exc_info.value.errors

    def test_preview_renders_without_records(
        self,
        test_proc_run,
        test_pipe_in_plan,
        test_user,
        registered_test_processor,
    ):
        """Preview returns the same script execute would, but writes nothing."""
        script = PipelineExecutor().preview(
            pipe_in_plan=test_pipe_in_plan,
            proc_run=test_proc_run,
            user=test_user,
            parameters={"test_param": 50},
        )

        assert script == "#!/bin/bash\necho 50"
        assert PipeExecution.objects.count() == 0

    def test_preview_accepts_unsaved_run(
        self,
        test_pipe_in_plan,
        test_msi_session,
        test_user,
        registered_test_processor,
    ):
        """Preview happens before the run exists, so an unsaved ProcRun must work."""
        from processes.models import ProcRun

        temp_run = ProcRun(name="run002", proc_plan=test_pipe_in_plan.plan, msi_session=test_msi_session)

        script = PipelineExecutor().preview(
            pipe_in_plan=test_pipe_in_plan,
            proc_run=temp_run,
            user=test_user,
            parameters={"test_param": 7},
        )

        assert script == "#!/bin/bash\necho 7"
        assert ProcRun.objects.filter(name="run002").count() == 0

    @patch("workflow.execution.RemoteJobSubmitter")
    def test_execute_materializes_cascade_defaults(
        self,
        mock_submitter_class,
        test_proc_run,
        test_pipe_in_plan,
        test_proc_software,
        test_user,
        registered_test_processor,
    ):
        """A ParameterDefaults value the form didn't post still reaches the stored parameters."""
        from processes.models import ParameterDefaults

        ParameterDefaults.objects.create(proc_software=test_proc_software, values={"test_param": 77})
        mock_submitter = MagicMock()
        mock_submitter.run_script.return_value = ("Submitted batch job 1", "")
        mock_submitter.last_script_path = "/scripts/test_script.sh"
        mock_submitter_class.return_value = mock_submitter

        result = PipelineExecutor().execute_pipe(
            pipe_in_plan=test_pipe_in_plan,
            proc_run=test_proc_run,
            user=test_user,
            parameters={},
            auth={"username": "test", "password": "pass"},
        )

        execution = PipeExecution.objects.get(id=result["pipe_execution_id"])
        assert execution.parameters["test_param"] == 77
        assert execution.script_content == "#!/bin/bash\necho 77"

    def test_cleared_default_must_be_posted(
        self,
        test_proc_run,
        test_pipe_in_plan,
        test_proc_software,
        test_user,
        registered_test_processor,
    ):
        """A row that nulls a key makes it required; leaving it out fails before render."""
        from processes.models import ParameterDefaults

        ParameterDefaults.objects.create(proc_software=test_proc_software, values={"test_param": None})

        with pytest.raises(ValidationError) as exc_info:
            PipelineExecutor().preview(
                pipe_in_plan=test_pipe_in_plan,
                proc_run=test_proc_run,
                user=test_user,
                parameters={},
            )

        assert exc_info.value.errors == ["Required parameter missing: test_param"]

    def test_cluster_not_allowed(
        self,
        test_proc_run,
        test_pipe_in_plan,
        test_user,
        registered_test_processor,
    ):
        """allowed_clusters on the software restricts where it may run."""
        software = test_pipe_in_plan.pipe.software
        software.allowed_clusters = ["czii"]
        software.save()

        with pytest.raises(ValidationError) as exc_info:
            PipelineExecutor().preview(
                pipe_in_plan=test_pipe_in_plan,
                proc_run=test_proc_run,
                user=test_user,
                parameters={"test_param": 1},
                cluster_id="bruno",
            )

        assert "not allowed" in exc_info.value.errors[0]


RESERVATION = {"runs": ["run007"]}


@pytest.fixture
def reserving_processor(test_processor_class):
    """A registered processor whose reservation feeds its script; records reserve/release calls."""
    from workflow.processors import _PROCESSOR_REGISTRY

    class ReservingProcessor(test_processor_class):
        reserved = []
        released = []

        def reserve_runs(self, run_context, params):
            self.reserved.append(dict(params))
            return RESERVATION

        def release_runs(self, run_context, reservation):
            self.released.append(reservation)

        def render_script(self, params, run_context):
            runs = params.get("_reserved_runs", {}).get("runs", ["none"])
            return f"#!/bin/bash\necho {runs[0]}"

    original_registry = _PROCESSOR_REGISTRY.copy()
    _PROCESSOR_REGISTRY["test_processor"] = ReservingProcessor

    yield ReservingProcessor

    _PROCESSOR_REGISTRY.clear()
    _PROCESSOR_REGISTRY.update(original_registry)


def _submitter(mock_submitter_class, side_effect=None):
    mock_submitter = MagicMock()
    mock_submitter.run_script.return_value = ("Submitted batch job 123456", "")
    mock_submitter.run_script.side_effect = side_effect
    mock_submitter.last_script_path = "/scripts/test_script.sh"
    mock_submitter_class.return_value = mock_submitter
    return mock_submitter


class TestReserveRuns:
    """processor.reserve_runs runs only for a real submission, and is released if it fails."""

    def test_default_reserves_nothing(self, test_processor_class):
        # test_execute_pipe pins the stored parameters, so no "_reserved_runs" key leaks in either.
        processor = test_processor_class()

        assert processor.reserve_runs(_bare_context({}), {"test_param": 1}) == {}
        assert processor.release_runs(_bare_context({}), {}) is None

    def _execute(self, test_pipe_in_plan, test_proc_run, test_user):
        return PipelineExecutor().execute_pipe(
            pipe_in_plan=test_pipe_in_plan,
            proc_run=test_proc_run,
            user=test_user,
            parameters={"test_param": 50},
            auth={"username": "test", "password": "pass"},
        )

    @patch("workflow.execution.RemoteJobSubmitter")
    def test_reservation_reaches_script_and_record(
        self, mock_submitter_class, test_proc_run, test_pipe_in_plan, test_user, reserving_processor
    ):
        _submitter(mock_submitter_class)

        result = self._execute(test_pipe_in_plan, test_proc_run, test_user)

        execution = PipeExecution.objects.get(id=result["pipe_execution_id"])
        assert execution.script_content == "#!/bin/bash\necho run007"
        assert execution.parameters["_reserved_runs"] == RESERVATION
        assert execution.parameters["test_param"] == 50
        assert reserving_processor.reserved == [{"test_param": 50}]
        assert reserving_processor.released == []

    @patch("workflow.execution.RemoteJobSubmitter")
    def test_released_when_submission_fails(
        self, mock_submitter_class, test_proc_run, test_pipe_in_plan, test_user, reserving_processor
    ):
        _submitter(mock_submitter_class, side_effect=RuntimeError("sbatch failed"))

        with pytest.raises(RuntimeError, match="sbatch failed"):
            self._execute(test_pipe_in_plan, test_proc_run, test_user)

        assert reserving_processor.released == [RESERVATION]
        assert PipeExecution.objects.count() == 0

    @patch.object(PipelineExecutor, "_create_execution_record", side_effect=RuntimeError("db down"))
    @patch("workflow.execution.RemoteJobSubmitter")
    def test_kept_when_record_creation_fails_after_submission(
        self, mock_submitter_class, _create, test_proc_run, test_pipe_in_plan, test_user, reserving_processor
    ):
        """The job was submitted and writes into the reserved runs, so they stay reserved."""
        _submitter(mock_submitter_class)

        with pytest.raises(RuntimeError, match="db down"):
            self._execute(test_pipe_in_plan, test_proc_run, test_user)

        assert reserving_processor.released == []

    def test_released_when_render_fails(self, test_proc_run, test_pipe_in_plan, test_user, reserving_processor):
        with (
            patch.object(reserving_processor, "render_script", side_effect=KeyError("boom")),
            pytest.raises(ValueError, match="Failed to render script"),
        ):
            self._execute(test_pipe_in_plan, test_proc_run, test_user)

        assert reserving_processor.released == [RESERVATION]

    def test_preview_never_reserves(self, test_proc_run, test_pipe_in_plan, test_user, reserving_processor):
        script = PipelineExecutor().preview(
            pipe_in_plan=test_pipe_in_plan,
            proc_run=test_proc_run,
            user=test_user,
            parameters={"test_param": 50},
        )

        assert script == "#!/bin/bash\necho none"
        assert reserving_processor.reserved == []
        assert reserving_processor.released == []


# API Endpoint Tests


@pytest.mark.django_db
class TestExecutionAPI:
    """Tests for execution API endpoints."""

    def test_list_available_processors(self, client, test_user, registered_test_processor):
        """Test listing available processors."""
        client.force_login(test_user)

        response = client.get("/workflow/v1/processors/")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["processors"]) > 0

        # Check test processor is in list
        processor_names = [p["name"] for p in data["processors"]]
        assert "test_processor" in processor_names

    def test_get_processor_schema_not_found(self, client, test_user):
        """Test getting schema for non-existent processor."""
        client.force_login(test_user)

        response = client.get("/workflow/v1/processors/nonexistent/schema/")

        assert response.status_code == 404
        data = response.json()
        assert data["success"] is False

    def test_get_execution_status(
        self,
        client,
        test_user,
        test_proc_run,
        test_pipe_in_plan,
    ):
        """Test getting execution status."""
        # Create a pipe execution
        execution = PipeExecution.objects.create(
            proc_run=test_proc_run,
            pipe_in_plan=test_pipe_in_plan,
            status="running",
            job_id="123456",
            parameters={"test": "value"},
        )

        client.force_login(test_user)

        response = client.get(f"/workflow/v1/execution/{execution.id}/status/")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["execution"]["id"] == execution.id
        assert data["execution"]["status"] == "running"
        assert data["execution"]["job_id"] == "123456"

    def test_check_dependencies(
        self,
        client,
        test_user,
        test_proc_run,
        test_pipe_in_plan,
    ):
        """Test checking dependencies endpoint."""
        client.force_login(test_user)

        response = client.get(
            f"/workflow/v1/execution/check_dependencies/"
            f"?pipe_in_plan_id={test_pipe_in_plan.id}&proc_run_id={test_proc_run.id}",
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["dependencies_met"] is True
        assert data["missing_dependencies"] == []

    def _preview(self, client, **overrides):
        body = {
            "processor": "test_processor",
            "session_id": "24nov10",
            "run_name": "run009",
            "parameters": {"test_param": 50},
            "cluster": "czii",
            **overrides,
        }
        return client.post("/workflow/v1/execution/preview/", body, content_type="application/json")

    def test_preview_script(self, client, test_user, test_pipe_in_plan, test_msi_session, registered_test_processor):
        client.force_login(test_user)

        response = self._preview(client)

        assert response.status_code == 200
        assert response.json() == {"success": True, "script_content": "#!/bin/bash\necho 50"}

    def test_preview_script_validation_error(
        self, client, test_user, test_pipe_in_plan, test_msi_session, registered_test_processor
    ):
        client.force_login(test_user)

        response = self._preview(client, parameters={"test_param": -5})

        assert response.status_code == 400
        assert response.json()["validation_errors"] == ["test_param must be non-negative"]

    def test_preview_script_missing_required(
        self, client, test_user, test_pipe_in_plan, test_msi_session, registered_test_processor
    ):
        """schema `required` is enforced server-side, with the same 400 shape as other validation."""
        client.force_login(test_user)

        response = self._preview(client, parameters={})

        assert response.status_code == 400
        assert response.json()["validation_errors"] == ["Required parameter missing: test_param"]

    def test_preview_script_unknown_cluster(
        self, client, test_user, test_pipe_in_plan, test_msi_session, registered_test_processor
    ):
        client.force_login(test_user)

        response = self._preview(client, cluster="nowhere")

        assert response.status_code == 400
        assert "nowhere" in response.json()["error"]


# ============================================================================
# Syncer Integration Tests
# ============================================================================


class TestSyncerIntegration:
    """Tests for syncer task startup and status monitoring."""

    @pytest.mark.parametrize(
        "processor_cls, syncer_path",
        [
            (DenoisETProcessor, "workflow.processors.denoiset.syncer.DenoiseSyncer"),
            (CopickProcessor, None),  # Copick writes its own outputs; no syncer by design
        ],
    )
    def test_on_job_submit_syncer(self, processor_cls, syncer_path):
        processor = processor_cls()
        run_context = MagicMock()

        with patch.object(processor, "_start_syncer_task") as mock_start:
            processor.on_job_submit(run_context, "job456")

        if syncer_path is None:
            mock_start.assert_not_called()
            return

        mock_start.assert_called_once_with(syncer_class_path=syncer_path, run_context=run_context, job_id="job456")
