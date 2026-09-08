"""
Tests for Generic Pipeline Execution Infrastructure

Tests the processor registry, execution engine, and API endpoints.
"""

from unittest.mock import MagicMock, Mock, patch

import pytest
from processes.models import PipeExecution, PipeInPlan
from workflow.execution import PipelineExecutor, RunContext, ValidationError
from workflow.processors import get_processor, list_processors, register_processor
from workflow.processors.base import BaseProcessor

# Test Fixtures


@pytest.fixture
def test_processor_class():
    """Create a test processor class."""

    class TestProcessor(BaseProcessor):
        name = "test_processor"
        display_name = "Test Processor"
        version = "1.0.0"
        cluster = "czii"

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


# Processor Registry Tests


class TestProcessorRegistry:
    """Tests for the processor registry system."""

    def test_register_processor(self, test_processor_class):
        """Test registering a processor."""
        from workflow.processors import _PROCESSOR_REGISTRY

        original_registry = _PROCESSOR_REGISTRY.copy()
        try:
            register_processor(test_processor_class)
            assert "test_processor" in _PROCESSOR_REGISTRY
            assert _PROCESSOR_REGISTRY["test_processor"] == test_processor_class
        finally:
            _PROCESSOR_REGISTRY.clear()
            _PROCESSOR_REGISTRY.update(original_registry)

    def test_register_processor_without_name_fails(self):
        """Test that registering a processor without a name fails."""

        class BadProcessor(BaseProcessor):
            # Missing name attribute
            pass

        with pytest.raises(ValueError, match="must define a 'name' class attribute"):
            register_processor(BadProcessor)

    def test_get_processor(self, registered_test_processor):
        """Test getting a processor by name."""
        processor = get_processor("test_processor")

        assert processor.name == "test_processor"
        assert processor.display_name == "Test Processor"
        assert processor.version == "1.0.0"
        assert processor.cluster == "czii"

    def test_get_nonexistent_processor_fails(self):
        """Test that getting a non-existent processor raises ValueError."""
        with pytest.raises(ValueError, match="Unknown processor"):
            get_processor("nonexistent")

    def test_list_processors(self, registered_test_processor):
        """Test listing all processors."""
        processors = list_processors()

        assert "test_processor" in processors
        assert processors["test_processor"] == registered_test_processor


# RunContext Tests


class TestRunContext:
    """Tests for RunContext data structure."""

    def test_run_context_creation(self, test_proc_run, test_pipe_in_plan, test_msi_session, test_user):
        """Test creating a RunContext."""
        context = RunContext(
            proc_run=test_proc_run,
            pipe_in_plan=test_pipe_in_plan,
            msi_session=test_msi_session,
            user=test_user,
            cluster_id="czii",
            run_number="run001",
            job_name="test_job_name",
            inputs={"test_input": "/path/to/input.txt"},
        )

        assert context.proc_run == test_proc_run
        assert context.pipe_in_plan == test_pipe_in_plan
        assert context.cluster_id == "czii"
        assert context.run_number == "run001"
        assert context.inputs["test_input"] == "/path/to/input.txt"

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

    def test_get_input_required(self, test_proc_run, test_pipe_in_plan, test_msi_session, test_user):
        """Test getting a required input."""
        context = RunContext(
            proc_run=test_proc_run,
            pipe_in_plan=test_pipe_in_plan,
            msi_session=test_msi_session,
            user=test_user,
            cluster_id="czii",
            run_number="run001",
            job_name="test_job_name",
            inputs={"aln": "/path/to/alignment.txt"},
        )

        assert context.get_input("aln") == "/path/to/alignment.txt"

    def test_get_input_missing_required_fails(self, test_proc_run, test_pipe_in_plan, test_msi_session, test_user):
        """Test that getting a missing required input fails."""
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

        with pytest.raises(ValueError, match="Required input 'aln' not found"):
            context.get_input("aln", required=True)

    def test_get_input_optional(self, test_proc_run, test_pipe_in_plan, test_msi_session, test_user):
        """Test getting an optional input."""
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

        result = context.get_input("optional_input", required=False)
        assert result is None


# PipelineExecutor Tests


class TestPipelineExecutor:
    """Tests for PipelineExecutor."""

    @patch("workflow.execution.RemoteJobSubmitter")
    def test_execute_pipe(
        self,
        mock_submitter_class,
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

    def test_preview_validation_fails(
        self,
        test_proc_run,
        test_pipe_in_plan,
        test_user,
        registered_test_processor,
    ):
        with pytest.raises(ValidationError) as exc_info:
            PipelineExecutor().preview(
                pipe_in_plan=test_pipe_in_plan,
                proc_run=test_proc_run,
                user=test_user,
                parameters={"test_param": -1},
            )

        assert "test_param must be non-negative" in exc_info.value.errors

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

    def test_check_dependencies_met_no_dependencies(
        self,
        test_proc_run,
        test_pipe_in_plan,
    ):
        """Test checking dependencies when there are none."""
        executor = PipelineExecutor()

        dependencies_met, missing = executor.check_dependencies_met(
            test_proc_run,
            test_pipe_in_plan,
        )

        assert dependencies_met is True
        assert missing == []


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

    def test_get_processor_schema(self, client, test_user, registered_test_processor):
        """Test getting processor schema."""
        client.force_login(test_user)

        response = client.get("/workflow/v1/processors/test_processor/schema/")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["processor"] == "test_processor"
        assert "schema" in data
        assert "display_name" in data
        assert "default_cluster" in data
        assert "allowed_clusters" in data

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

    def test_list_run_executions(
        self,
        client,
        test_user,
        test_proc_run,
        test_pipe_in_plan,
        test_pipe,
    ):
        """Test listing executions for a run."""
        # Create second pipe_in_plan for second execution
        # (unique_together constraint requires unique proc_run + pipe_in_plan pairs)
        pipe_in_plan_2 = PipeInPlan.objects.create(
            plan=test_proc_run.proc_plan,
            pipe=test_pipe,
            step=2,
            name="test_step_2",
        )

        # Create some executions
        PipeExecution.objects.create(
            proc_run=test_proc_run,
            pipe_in_plan=test_pipe_in_plan,
            status="completed",
            job_id="111111",
        )
        PipeExecution.objects.create(
            proc_run=test_proc_run,
            pipe_in_plan=pipe_in_plan_2,
            status="running",
            job_id="222222",
        )

        client.force_login(test_user)

        response = client.get(f"/workflow/v1/execution/run/{test_proc_run.id}/")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["executions"]) == 2
        assert data["proc_run"]["name"] == "run001"

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
        assert "dependencies_met" in data
        assert "missing_dependencies" in data

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

    def test_status_monitoring_scheduled_on_execution(
        self,
        test_msi_session,
        test_proc_run,
        test_pipe_in_plan,
        test_user,
        test_proc_software,
        registered_test_processor,
    ):
        """Test that Django-Q status monitoring is scheduled after job submission."""
        # Update software to use test processor
        test_proc_software.processor_class = "test_processor"
        test_proc_software.save()

        executor = PipelineExecutor()

        # Mock RemoteJobSubmitter to avoid actual SSH
        with patch("workflow.execution.RemoteJobSubmitter") as mock_submitter_class:
            mock_submitter = Mock()
            mock_submitter.last_script_path = "/remote/script.sh"
            mock_submitter.run_script.return_value = ("Submitted batch job 123456", "")
            mock_submitter_class.return_value = mock_submitter

            # Mock schedule_pipe_execution_monitoring
            with patch("processes.tasks.schedule_pipe_execution_monitoring") as mock_schedule:
                mock_schedule.return_value = "schedule_id_123"

                result = executor.execute_pipe(
                    pipe_in_plan=test_pipe_in_plan,
                    proc_run=test_proc_run,
                    user=test_user,
                    parameters={"test_param": 50},
                    auth={"username": "test", "password": "test"},
                )

                # Verify monitoring was scheduled
                assert mock_schedule.called
                call_args = mock_schedule.call_args[0]
                assert call_args[0] == result["pipe_execution_id"]  # PipeExecution ID
                assert call_args[1] == "123456"  # Job ID

    def test_aretomo3_processor_spawns_syncer(
        self,
        test_msi_session,
        test_proc_run,
        test_pipe_in_plan,
        test_user,
    ):
        """Test that AreTomo3 processor starts syncer task via helper method."""
        from workflow.execution import RunContext
        from workflow.processors.aretomo3 import AreTomo3Processor

        run_context = RunContext(
            proc_run=test_proc_run,
            pipe_in_plan=test_pipe_in_plan,
            msi_session=test_msi_session,
            user=test_user,
            cluster_id="czii",
            run_number="run001",
            job_name="test_job_name",
            inputs={},
        )

        processor = AreTomo3Processor()

        # Mock _start_syncer_task (the new method used by AreTomo3)
        with patch.object(processor, "_start_syncer_task") as mock_start:
            processor.on_job_submit(run_context, "job123")

            # Verify helper was called with correct arguments
            assert mock_start.called
            call_kwargs = mock_start.call_args[1]
            # Check syncer class path includes aretomo3
            assert "aretomo3" in call_kwargs["syncer_class_path"]
            assert call_kwargs["run_context"] == run_context
            assert call_kwargs["job_id"] == "job123"

    def test_denoiset_processor_spawns_syncer(
        self,
        test_msi_session,
        test_proc_run,
        test_pipe_in_plan,
        test_user,
    ):
        """Test that DenoisET processor starts syncer task via helper method."""
        from workflow.execution import RunContext
        from workflow.processors.denoiset import DenoisETProcessor

        run_context = RunContext(
            proc_run=test_proc_run,
            pipe_in_plan=test_pipe_in_plan,
            msi_session=test_msi_session,
            user=test_user,
            cluster_id="czii",
            run_number="run001",
            job_name="test_job_name",
            inputs={},
        )

        processor = DenoisETProcessor()

        # Mock _start_syncer_task (the new method used by DenoisET)
        with patch.object(processor, "_start_syncer_task") as mock_start:
            processor.on_job_submit(run_context, "job456")

            # Verify helper was called with correct arguments
            assert mock_start.called
            call_kwargs = mock_start.call_args[1]
            # Check syncer class path includes denoiset
            assert "denoiset" in call_kwargs["syncer_class_path"]
            assert call_kwargs["run_context"] == run_context
            assert call_kwargs["job_id"] == "job456"

    def test_copick_processor_no_syncer(
        self,
        test_msi_session,
        test_proc_run,
        test_pipe_in_plan,
        test_user,
    ):
        """Test that Copick processor does not spawn syncer (as per design)."""
        from workflow.execution import RunContext
        from workflow.processors.copick import CopickProcessor

        run_context = RunContext(
            proc_run=test_proc_run,
            pipe_in_plan=test_pipe_in_plan,
            msi_session=test_msi_session,
            user=test_user,
            cluster_id="czii",
            run_number="run001",
            job_name="test_job_name",
            inputs={},
        )

        processor = CopickProcessor()

        with patch.object(processor, "_start_syncer_task") as mock_start:
            # on_job_submit should not start a syncer for Copick
            processor.on_job_submit(run_context, "job789")

            # Verify helper was NOT called
            assert not mock_start.called
