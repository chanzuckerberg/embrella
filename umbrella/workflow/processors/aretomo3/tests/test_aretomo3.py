"""
Tests for AreTomo3 processor implementation.
"""

from unittest.mock import MagicMock, patch

import pytest
from django.utils import timezone
from processes.models import (
    Pipe,
    PipeInPlan,
    ProcPlan,
    ProcRun,
    ProcSoftware,
    Task,
)
from stores.models import DataKind, FilePattern, PathType
from tem.models import (
    GAIN_ROLE,
    CalibratedPixelSize,
    Camera,
    ImagingWorkflow,
    Magnification,
    Microscope,
    MsiSession,
    SessionPlan,
    SessionPlanPathBinding,
    Software,
)

from workflow.execution import PipelineExecutor, RunContext
from workflow.processors import get_processor

# The test camera's gain template; a Falcon4i-style shared folder.
GAIN_DIR = "/test/gain/"
LIST_GAIN_FILES = "workflow.processors.aretomo3.processor.list_gain_files"


@pytest.fixture
def aretomo3_processor():
    """Get the AreTomo3 processor instance."""
    return get_processor("aretomo3")


@pytest.fixture
def gain_path_type(db, test_msi_session):
    """Give the session's camera a gain template, and return it."""
    camera = test_msi_session.session_plan.camera
    camera.gain = PathType.objects.create(data_kind=DataKind.objects.create(data_type="gain"), overlay_path=GAIN_DIR)
    camera.save(update_fields=["gain"])
    return camera.gain


@pytest.fixture
def test_msi_session(db):
    """Create a test MSI session."""
    # Create required related objects
    microscope = Microscope.objects.create(name="TestScope", cs=2.7)
    camera = Camera.objects.create(
        name="TestCamera",
        root_dir="/test/root",
        frame_format="eer",
        initial_frame_base_dir="/test/frames",
    )
    imaging_workflow = ImagingWorkflow.objects.create(imaging_mode="tem", workflow="tomo")
    # An mdocs template, so views resolving the session's mdoc directory (validate_session)
    # get a real path rather than the "software emits no mdocs" short-circuit.
    software = Software.objects.create(
        name="TestSoftware",
        mdocs=PathType.objects.create(
            data_kind=DataKind.objects.create(data_type="mdoc"),
            overlay_path="/test/root/{msi_session}/",
        ),
    )

    session_plan = SessionPlan.objects.create(
        scope=microscope,
        camera=camera,
        imaging_workflow=imaging_workflow,
        software=software,
    )

    return MsiSession.objects.create(
        name="24nov10",
        session_plan=session_plan,
    )


@pytest.fixture
def test_aretomo3_software(db):
    """Create AreTomo3 software entry."""
    task = Task.objects.create(name="tomographic_reconstruction")
    software = ProcSoftware.objects.create(
        name="aretomo3",
        version="2.2.2_07-11-2025",
        processor_class="aretomo3",
        default_cluster="czii",
    )
    software.capable_tasks.add(task)
    return software


@pytest.fixture
def test_pipe(db, test_aretomo3_software):
    """Create a test pipe."""
    return Pipe.objects.create(
        name="aretomo3_basic",
        software=test_aretomo3_software,
    )


@pytest.fixture
def test_proc_plan(db):
    """Create a test processing plan."""
    return ProcPlan.objects.create(
        name="czii-live",
    )


@pytest.fixture
def test_pipe_in_plan(db, test_proc_plan, test_pipe):
    """Create a test pipe in plan."""
    return PipeInPlan.objects.create(
        plan=test_proc_plan,
        pipe=test_pipe,
        step=1,
        name="aretomo3_step",
    )


@pytest.fixture
def test_proc_run(db, test_proc_plan, test_msi_session):
    """Create a test processing run."""
    return ProcRun.objects.create(
        name="run001",
        proc_plan=test_proc_plan,
        msi_session=test_msi_session,
    )


@pytest.fixture
def test_run_context(test_proc_run, test_pipe_in_plan, test_msi_session, test_user):
    """Create a test RunContext."""
    return RunContext(
        proc_run=test_proc_run,
        pipe_in_plan=test_pipe_in_plan,
        msi_session=test_msi_session,
        user=test_user,
        cluster_id="czii",
        run_number="run001",
        job_name="aretomo3_msi_24nov10_czii-live-run001_aretomo3_basic",
        inputs={},  # AreTomo3 doesn't require inputs from previous steps
    )


class TestAreTomo3Processor:
    """Tests for AreTomo3 processor."""

    def test_processor_registered(self, aretomo3_processor):
        """Test that AreTomo3 processor is registered."""
        assert aretomo3_processor is not None
        assert aretomo3_processor.name == "aretomo3"
        assert aretomo3_processor.display_name == "AreTomo3"

    def test_parameter_schema(self, aretomo3_processor):
        """Test parameter schema structure."""
        schema = aretomo3_processor.get_parameter_schema()

        assert schema["type"] == "object"
        assert "properties" in schema
        assert "required" in schema

        # Check required parameters
        required = schema["required"]
        assert "pixel_size" in required

        # Check parameter properties
        props = schema["properties"]
        assert "pixel_size" in props
        assert props["pixel_size"]["type"] == "number"
        assert "frame_dose" in props  # Optional but still defined

    def test_validate_parameters_valid(self, aretomo3_processor):
        """Test validation with valid parameters."""
        params = {
            "pixel_size": 2.0,
            "frame_dose": 1.5,
        }

        errors = aretomo3_processor.validate_parameters(params)
        assert errors == []

    def test_validate_parameters_eer_mcbin_mismatch(self, aretomo3_processor):
        """Test validation fails when EerSampling and McBin are mismatched."""
        params = {
            "pixel_size": 2.0,
            "frame_dose": 1.5,
            "eer_sampling": 2,
            "mc_bin": 1,  # Should be 2 when eer_sampling is 2
        }

        errors = aretomo3_processor.validate_parameters(params)
        assert len(errors) > 0
        assert any("EerSampling" in err or "McBin" in err for err in errors)

    def test_validate_parameters_advanced_missing(self, aretomo3_processor):
        """Test validation fails when use_advanced_params is true but advanced params are missing."""
        params = {
            "pixel_size": 2.0,
            "frame_dose": 1.5,
            "use_advanced_params": True,
            # Missing tilt_axis, vol_z, align_z
        }

        errors = aretomo3_processor.validate_parameters(params)
        assert len(errors) > 0

    def test_render_script_basic(self, aretomo3_processor, test_run_context, gain_path_type):
        """Test rendering basic AreTomo3 script."""
        params = {
            "pixel_size": 2.0,
            "frame_dose": 1.5,
            "gain_file_name": "somegainfile.gain",
        }

        script = aretomo3_processor.render_script(params, test_run_context)

        # Check script content
        assert "#!/bin/bash" in script
        assert 'project_name="24nov10"' in script
        assert 'run_number="run001"' in script
        assert 'pix_size="2.0"' in script
        assert 'frame_dose="1.5"' in script
        assert f'gain_fn="{GAIN_DIR}somegainfile.gain"' in script

        # Check calculated binning
        # 5 / 2.0 = 2.5, 10 / 2.0 = 5.0
        assert "tomo_bin_5A=2.5" in script
        assert "tomo_bin_10A=5.0" in script

    def test_path_resolver_passes_absolute_paths_through(self, aretomo3_processor):
        assert aretomo3_processor._format_cli_path_resolver(" /refs/defect.txt ", {}) == "/refs/defect.txt"
        assert aretomo3_processor._format_cli_path_resolver("", {}) == ""


@pytest.mark.django_db
class TestGainFilePath:
    """The -Gain path: absolute wins; else the session's gain directory, resolved per plan and cluster."""

    def resolve(self, processor, run_context, name):
        return processor._resolve_gain_file_path({"gain_file_name": name}, run_context)["gain_file_path"]

    def test_absolute_path_skips_resolution(self, aretomo3_processor, test_run_context):
        assert self.resolve(aretomo3_processor, test_run_context, "/elsewhere/ref.gain") == "/elsewhere/ref.gain"

    def test_joins_onto_camera_default(self, aretomo3_processor, test_run_context, gain_path_type):
        assert self.resolve(aretomo3_processor, test_run_context, "ref.gain") == f"{GAIN_DIR}ref.gain"

    def test_plan_binding_wins(self, aretomo3_processor, test_run_context, gain_path_type):
        beside_frames = PathType.objects.create(data_kind=gain_path_type.data_kind, overlay_path="/k3f/{msi_session}/")
        SessionPlanPathBinding.objects.create(
            session_plan=test_run_context.msi_session.session_plan, role=GAIN_ROLE, path_type=beside_frames
        )
        assert self.resolve(aretomo3_processor, test_run_context, "ref.dm4") == "/k3f/24nov10/ref.dm4"

    def test_no_directory_is_an_error(self, aretomo3_processor, test_run_context):
        with pytest.raises(ValueError, match="resolves no gain directory"):
            self.resolve(aretomo3_processor, test_run_context, "ref.gain")

    @patch(LIST_GAIN_FILES)
    def test_empty_name_picks_newest(self, mock_list, aretomo3_processor, test_run_context, gain_path_type):
        pattern = FilePattern.objects.create(
            data_kind=gain_path_type.data_kind, label="gain", list_glob="*.gain", regex=r"^(?P<stem>.+)\.gain$"
        )
        gain_path_type.file_pattern = pattern
        gain_path_type.save()
        mock_list.return_value = {"success": True, "files": [{"filename": "newest.gain"}, {"filename": "older.gain"}]}

        assert self.resolve(aretomo3_processor, test_run_context, "") == f"{GAIN_DIR}newest.gain"
        mock_list.assert_called_once_with(GAIN_DIR, cluster_id="czii", file_pattern=pattern)

    @patch(LIST_GAIN_FILES, return_value={"success": False, "files": [], "error": "ssh down"})
    def test_empty_name_with_failed_listing_is_an_error(self, _, aretomo3_processor, test_run_context, gain_path_type):
        with pytest.raises(ValueError, match="ssh down"):
            self.resolve(aretomo3_processor, test_run_context, "")


@pytest.mark.django_db
class TestDynamicOptions:
    """views.get_dynamic_options lists gain files for the session on the requested cluster."""

    FETCH = "workflow.processors.aretomo3.views.gain_file_fetcher.list_gain_files"

    def options(self, rf, session_id, query=""):
        from workflow.processors.aretomo3.views import get_dynamic_options

        response = get_dynamic_options(rf.get(f"/?{query}"), session_id)
        return __import__("json").loads(response.content)["options"]["gain_file_name"]

    @patch(FETCH)
    def test_lists_for_session_on_requested_cluster(self, mock_list, rf, test_msi_session, gain_path_type):
        mock_list.return_value = {
            "success": True,
            "files": [{"filename": "b.gain", "modified_time": "t"}, {"filename": "a.gain", "modified_time": "t"}],
        }

        options = self.options(rf, test_msi_session.name, "cluster_id=bruno")

        assert [o["value"] for o in options] == ["b.gain", "a.gain"]
        assert options[0]["label"] == "b.gain (most recent)"
        mock_list.assert_called_once_with(GAIN_DIR, cluster_id="bruno", file_pattern=None)

    @patch("workflow.processors.aretomo3.views.get_default_cluster_id", return_value="the-default")
    @patch(FETCH, return_value={"success": True, "files": []})
    def test_defaults_the_cluster(self, mock_list, _, rf, test_msi_session, gain_path_type):
        self.options(rf, test_msi_session.name)
        assert mock_list.call_args.kwargs["cluster_id"] == "the-default"

    @patch(FETCH)
    def test_empty_without_session_or_directory(self, mock_list, rf, test_msi_session):
        assert self.options(rf, None) == []
        assert self.options(rf, "nope") == []
        assert self.options(rf, test_msi_session.name) == []  # no gain PathType anywhere
        mock_list.assert_not_called()

    def test_get_slurm_options(self, aretomo3_processor):
        """Test SLURM options."""
        options = aretomo3_processor.get_default_slurm_options()

        assert options["partition"] == "gpu"
        assert options["gpus"] == 8
        assert options["nodes"] == 1

    @patch("processes.tasks.start_syncer_monitoring")
    def test_on_job_submit_hook(self, mock_start_syncer, aretomo3_processor, test_run_context):
        """Test on_job_submit hook triggers syncer via Django-Q task."""
        job_id = "123456"

        # Mock the Django-Q task function
        mock_start_syncer.return_value = "mock-task-id"

        # Should not raise exception
        aretomo3_processor.on_job_submit(test_run_context, job_id)

        # Verify syncer task was started
        assert mock_start_syncer.called
        call_kwargs = mock_start_syncer.call_args.kwargs
        assert call_kwargs["job_id"] == job_id
        assert call_kwargs["session_name"] == test_run_context.msi_session.name
        assert call_kwargs["run_id"] == test_run_context.run_number


def _set_magnification(session):
    mag = Magnification.objects.create(scope=session.session_plan.scope, mode="SA", nominal_mag=50000, index=0)
    session.magnification = mag
    session.save()
    return mag


@pytest.mark.django_db
class TestSessionDefaults:
    """AreTomo3Processor.session_defaults derives pixel_size from calibration data."""

    def test_pixel_size_when_calibration_exists(self, aretomo3_processor, test_msi_session):
        mag = _set_magnification(test_msi_session)
        CalibratedPixelSize.objects.create(
            mag=mag,
            camera=test_msi_session.session_plan.camera,
            pixel_spacing=2.5,
            calibrated_at=timezone.now(),
        )

        assert aretomo3_processor.session_defaults(test_msi_session) == {"pixel_size": 2.5}

    def test_empty_when_no_magnification(self, aretomo3_processor, test_msi_session):
        assert aretomo3_processor.session_defaults(test_msi_session) == {}

    def test_empty_when_no_calibration(self, aretomo3_processor, test_msi_session):
        _set_magnification(test_msi_session)

        assert aretomo3_processor.session_defaults(test_msi_session) == {}


@pytest.mark.django_db
class TestGetSessionInfo:
    """views.get_session_info describes the session; it decides no parameter values."""

    def test_magnification_block(self, test_msi_session):
        from workflow.processors.aretomo3.views import get_session_info

        _set_magnification(test_msi_session)

        info = get_session_info(test_msi_session)

        assert info["magnification"]["nominal_mag"] == 50000
        assert info["magnification"]["pixel_size"] is None
        # MDOC validation lives in validate_session, not here
        assert "pixel_size_validation" not in info["magnification"]

    def test_minimal_session(self, test_msi_session):
        from workflow.processors.aretomo3.views import get_session_info

        assert get_session_info(test_msi_session) == {"user": None}


@pytest.mark.django_db
class TestValidateSession:
    """Tests for validate_session returning MDOC magnification validation."""

    @patch("workflow.processors.aretomo3.views.mdoc_reader.read_mdoc_magnification")
    def test_magnification_match(self, mock_mdoc, test_msi_session, rf):
        """validate_session returns mismatch=false when magnifications match."""
        from workflow.processors.aretomo3.views import validate_session

        session = test_msi_session
        microscope = session.session_plan.scope

        mag = Magnification.objects.create(scope=microscope, mode="SA", nominal_mag=50000, index=0)
        session.magnification = mag
        session.save()

        mock_mdoc.return_value = {
            "success": True,
            "magnification": 50000,
            "mdoc_file": "Position_1.mdoc",
            "error": None,
        }

        request = rf.get("/?cluster_id=bruno")
        response = validate_session(request, session_id=session.name)
        data = response.json() if hasattr(response, "json") else __import__("json").loads(response.content)

        assert data["success"] is True
        assert data["validation"]["mismatch"] is False
        assert data["validation"]["mdoc_magnification"] == 50000
        assert mock_mdoc.call_args.kwargs["cluster_id"] == "bruno"

    @patch("workflow.processors.aretomo3.views.mdoc_reader.read_mdoc_magnification")
    def test_magnification_mismatch(self, mock_mdoc, test_msi_session, rf):
        """validate_session returns mismatch=true when magnifications differ."""
        from workflow.processors.aretomo3.views import validate_session

        session = test_msi_session
        microscope = session.session_plan.scope

        mag = Magnification.objects.create(scope=microscope, mode="SA", nominal_mag=50000, index=0)
        session.magnification = mag
        session.save()

        mock_mdoc.return_value = {
            "success": True,
            "magnification": 81000,
            "mdoc_file": "Position_1.mdoc",
            "error": None,
        }

        request = rf.get("/")
        response = validate_session(request, session_id=session.name)
        data = response.json() if hasattr(response, "json") else __import__("json").loads(response.content)

        assert data["validation"]["mismatch"] is True
        assert "warning" in data["validation"]

    @patch("workflow.processors.aretomo3.views.mdoc_reader.read_mdoc_magnification")
    def test_mdoc_error(self, mock_mdoc, test_msi_session, rf):
        """validate_session returns error when MDOC read fails."""
        from workflow.processors.aretomo3.views import validate_session

        mock_mdoc.return_value = {
            "success": False,
            "magnification": None,
            "mdoc_file": None,
            "error": "No MDOC files found",
        }

        request = rf.get("/")
        response = validate_session(request, session_id=test_msi_session.name)
        data = response.json() if hasattr(response, "json") else __import__("json").loads(response.content)

        assert data["success"] is True
        assert data["validation"]["error"] == "No MDOC files found"

    def test_no_session_id(self, rf):
        """validate_session returns empty validation when no session_id."""
        from workflow.processors.aretomo3.views import validate_session

        request = rf.get("/")
        response = validate_session(request, session_id=None)
        data = response.json() if hasattr(response, "json") else __import__("json").loads(response.content)

        assert data["success"] is True
        assert data["validation"] == {}


@pytest.mark.django_db
class TestAreTomo3Integration:
    """Integration tests for AreTomo3 execution flow."""

    @patch("workflow.execution.RemoteJobSubmitter")
    def test_full_execution_flow(
        self,
        mock_submitter_class,
        test_proc_run,
        test_pipe_in_plan,
        test_user,
        gain_path_type,
    ):
        """Test full AreTomo3 execution flow."""
        # Mock the RemoteJobSubmitter
        mock_submitter = MagicMock()
        mock_submitter.run_script.return_value = ("Submitted batch job 123456\nSubmitted batch job 123457", "")
        mock_submitter.last_script_path = "/scripts/aretomo3_script.sh"
        mock_submitter_class.return_value = mock_submitter

        executor = PipelineExecutor()

        params = {
            "pixel_size": 2.0,
            "frame_dose": 1.5,
            "gain_file_name": "somegainfile.gain",
        }

        result = executor.execute_pipe(
            pipe_in_plan=test_pipe_in_plan,
            proc_run=test_proc_run,
            user=test_user,
            parameters=params,
            auth={"username": "test", "password": "pass"},
        )

        # Verify result
        assert result["status"] == "submitted"
        assert result["job_id"] is not None
        assert "pipe_execution_id" in result

        # Verify job submission was called
        mock_submitter.connect.assert_called_once()
        mock_submitter.run_script.assert_called_once()
        mock_submitter.close.assert_called_once()
