"""
Tests for AreTomo3 processor implementation.
"""

from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth.models import User
from processes.models import (
    Pipe,
    PipeInPlan,
    ProcPlan,
    ProcRun,
    ProcSoftware,
    Task,
)
from tem.models import Camera, ImagingWorkflow, Microscope, MsiSession, SessionPlan, Software
from workflow.execution import PipelineExecutor, RunContext
from workflow.processors import get_processor


@pytest.fixture
def aretomo3_processor():
    """Get the AreTomo3 processor instance."""
    return get_processor('aretomo3')


@pytest.fixture
def test_user(db):
    """Create a test user."""
    return User.objects.create_user(
        username='testuser',
        email='test@example.com',
        password='testpass123',
    )


@pytest.fixture
def test_msi_session(db):
    """Create a test MSI session."""
    # Create required related objects
    microscope = Microscope.objects.create(name='TestScope', cs=2.7)
    camera = Camera.objects.create(
        name='TestCamera',
        root_dir='/test/root',
        frame_format='eer',
        initial_frame_base_dir='/test/frames',
    )
    imaging_workflow = ImagingWorkflow.objects.create(imaging_mode='tem', workflow='tomo')
    software = Software.objects.create(name='TestSoftware')

    session_plan = SessionPlan.objects.create(
        scope=microscope,
        camera=camera,
        imaging_workflow=imaging_workflow,
        software=software,
    )

    return MsiSession.objects.create(
        name='24nov10',
        session_plan=session_plan,
    )


@pytest.fixture
def test_aretomo3_software(db):
    """Create AreTomo3 software entry."""
    task = Task.objects.create(name='tomographic_reconstruction')
    software = ProcSoftware.objects.create(
        name='aretomo3',
        version='2.2.2_07-11-2025',
        processor_class='aretomo3',
        default_cluster='czii',
        script_directory='/hpc/projects/group.czii/krios1.processing/aretomo3/scripts',
    )
    software.capable_tasks.add(task)
    return software


@pytest.fixture
def test_pipe(db, test_aretomo3_software):
    """Create a test pipe."""
    return Pipe.objects.create(
        name='aretomo3_basic',
        software=test_aretomo3_software,
    )


@pytest.fixture
def test_proc_plan(db):
    """Create a test processing plan."""
    return ProcPlan.objects.create(
        name='czii-live',
    )


@pytest.fixture
def test_pipe_in_plan(db, test_proc_plan, test_pipe):
    """Create a test pipe in plan."""
    return PipeInPlan.objects.create(
        plan=test_proc_plan,
        pipe=test_pipe,
        step=1,
        name='aretomo3_step',
    )


@pytest.fixture
def test_proc_run(db, test_proc_plan, test_msi_session):
    """Create a test processing run."""
    return ProcRun.objects.create(
        name='run001',
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
        cluster_id='czii',
        run_number='run001',
        job_name='aretomo3_msi_24nov10_czii-live-run001_aretomo3_basic',
        inputs={},  # AreTomo3 doesn't require inputs from previous steps
    )


class TestAreTomo3Processor:
    """Tests for AreTomo3 processor."""

    def test_processor_registered(self, aretomo3_processor):
        """Test that AreTomo3 processor is registered."""
        assert aretomo3_processor is not None
        assert aretomo3_processor.name == 'aretomo3'
        assert aretomo3_processor.display_name == 'AreTomo3'

    def test_parameter_schema(self, aretomo3_processor):
        """Test parameter schema structure."""
        schema = aretomo3_processor.get_parameter_schema()

        assert schema['type'] == 'object'
        assert 'properties' in schema
        assert 'required' in schema

        # Check required parameters
        required = schema['required']
        assert 'pixel_size' in required

        # Check parameter properties
        props = schema['properties']
        assert 'pixel_size' in props
        assert props['pixel_size']['type'] == 'number'
        assert 'frame_dose' in props  # Optional but still defined

    def test_validate_parameters_valid(self, aretomo3_processor):
        """Test validation with valid parameters."""
        params = {
            'pixel_size': 2.0,
            'frame_dose': 1.5,
        }

        errors = aretomo3_processor.validate_parameters(params)
        assert errors == []

    def test_validate_parameters_eer_mcbin_mismatch(self, aretomo3_processor):
        """Test validation fails when EerSampling and McBin are mismatched."""
        params = {
            'pixel_size': 2.0,
            'frame_dose': 1.5,
            'eer_sampling': 2,
            'mc_bin': 1,  # Should be 2 when eer_sampling is 2
        }

        errors = aretomo3_processor.validate_parameters(params)
        assert len(errors) > 0
        assert any('EerSampling' in err or 'McBin' in err for err in errors)

    def test_validate_parameters_advanced_missing(self, aretomo3_processor):
        """Test validation fails when use_advanced_params is true but advanced params are missing."""
        params = {
            'pixel_size': 2.0,
            'frame_dose': 1.5,
            'use_advanced_params': True,
            # Missing tilt_axis, vol_z, align_z
        }

        errors = aretomo3_processor.validate_parameters(params)
        assert len(errors) > 0

    def test_render_script_basic(self, aretomo3_processor, test_run_context):
        """Test rendering basic AreTomo3 script."""
        params = {
            'pixel_size': 2.0,
            'frame_dose': 1.5,
            'gain_file_name': 'somegainfile.gain',
        }

        script = aretomo3_processor.render_script(params, test_run_context)

        # Check script content
        assert '#!/bin/bash' in script
        assert 'project_name="24nov10"' in script
        assert 'run_number="run001"' in script
        assert 'pix_size="2.0"' in script
        assert 'frame_dose="1.5"' in script
        assert 'gain_fn="/hpc/instruments/czii.krios1/OffloadData/ImagesForProcessing/EF-Falcon/300kV/somegainfile.gain"' in script

        # Check calculated binning
        # 5 / 2.0 = 2.5, 10 / 2.0 = 5.0
        assert 'tomo_bin_5A=2.5' in script
        assert 'tomo_bin_10A=5.0' in script

    def test_parse_output_paths(self, aretomo3_processor, test_run_context):
        """Test parsing expected output paths."""
        paths = aretomo3_processor.parse_output_paths(test_run_context)

        assert len(paths) > 0

        # Check path types
        types = [p['type'] for p in paths]
        assert 'rec' in types  # Reconstruction volumes
        assert 'aln' in types  # Alignment data
        assert 'meta' in types  # Session metadata

        # Check patterns contain session and run
        for path_spec in paths:
            assert '24nov10' in path_spec['pattern']
            assert 'run001' in path_spec['pattern']

    def test_get_slurm_options(self, aretomo3_processor):
        """Test SLURM options."""
        options = aretomo3_processor.get_default_slurm_options()

        assert options['partition'] == 'gpu'
        assert options['gpus'] == 8
        assert options['nodes'] == 1

    @patch('processes.tasks.start_syncer_monitoring')
    def test_on_job_submit_hook(self, mock_start_syncer, aretomo3_processor, test_run_context):
        """Test on_job_submit hook triggers syncer via Django-Q task."""
        job_id = '123456'

        # Mock the Django-Q task function
        mock_start_syncer.return_value = 'mock-task-id'

        # Should not raise exception
        aretomo3_processor.on_job_submit(test_run_context, job_id)

        # Verify syncer task was started
        assert mock_start_syncer.called
        call_kwargs = mock_start_syncer.call_args.kwargs
        assert call_kwargs['job_id'] == job_id
        assert call_kwargs['session_name'] == test_run_context.msi_session.name
        assert call_kwargs['run_id'] == test_run_context.run_number


@pytest.mark.django_db
class TestAreTomo3Integration:
    """Integration tests for AreTomo3 execution flow."""

    @patch('workflow.execution.RemoteJobSubmitter')
    def test_full_execution_flow(
        self,
        mock_submitter_class,
        test_proc_run,
        test_pipe_in_plan,
        test_user,
    ):
        """Test full AreTomo3 execution flow."""
        # Mock the RemoteJobSubmitter
        mock_submitter = MagicMock()
        mock_submitter.run_script.return_value = ("Submitted batch job 123456\nSubmitted batch job 123457", "")
        mock_submitter.last_script_path = "/scripts/aretomo3_script.sh"
        mock_submitter_class.return_value = mock_submitter

        executor = PipelineExecutor()

        params = {
            'pixel_size': 2.0,
            'frame_dose': 1.5,
            'gain_file_name': 'somegainfile.gain',
        }

        result = executor.execute_pipe(
            pipe_in_plan=test_pipe_in_plan,
            proc_run=test_proc_run,
            user=test_user,
            parameters=params,
            auth={'username': 'test', 'password': 'pass'},
        )

        # Verify result
        assert result['status'] == 'submitted'
        assert result['job_id'] is not None
        assert 'pipe_execution_id' in result

        # Verify job submission was called
        mock_submitter.connect.assert_called_once()
        mock_submitter.run_script.assert_called_once()
        mock_submitter.close.assert_called_once()
