"""
Tests for processes services (PipelineDataService, RunCreationService).
"""

from unittest.mock import Mock, patch

import pytest
from django.test import TestCase
from tem.models import MsiSession

from processes.models import Pipe, PipeInPlan, ProcPlan, ProcRun
from processes.services import PipelineDataService, RunCreationService

pytestmark = pytest.mark.django_db


class TestPipelineDataService(TestCase):
    """Tests for PipelineDataService."""

    def setUp(self):
        """Set up test fixtures."""
        # Create mock objects for testing
        self.msi_session = Mock(spec=MsiSession)
        self.proc_plan = Mock(spec=ProcPlan)
        self.proc_run = Mock(spec=ProcRun)
        self.proc_run.proc_plan = self.proc_plan
        self.proc_run.msi_session = self.msi_session

    @patch("processes.services.pipeline_data.PipeInPlan")
    @patch("processes.services.pipeline_data.Path")
    @patch("processes.services.pipeline_data.RunPipeData")
    @patch("processes.services.pipeline_data.fill_place_holders")
    def test_save_pipe_run_data(self, mock_fill, mock_run_pipe_data, mock_path, mock_pipe_in_plan):
        """Test save_pipe_run_data creates RunPipeData records correctly."""
        # Setup mocks
        pipe_mock = Mock(spec=Pipe)
        p_out_mock = Mock()
        p_out_mock.static_path.static_path = "/static/path"
        p_out_mock.overlay_path = "/overlay/path"
        pipe_mock.output.all.return_value = [p_out_mock]

        pipe_in_plan_mock = Mock(spec=PipeInPlan)
        pipe_in_plan_mock.pipe = pipe_mock
        pipe_in_plan_mock.get_replacement_map.return_value = {"session": "test_session"}

        mock_pipe_in_plan.objects.filter.return_value = [pipe_in_plan_mock]
        mock_fill.side_effect = ["/filled/static", "/filled/overlay"]
        mock_path.objects.create.return_value = Mock()
        mock_run_pipe_data.objects.create.return_value = Mock()

        # Execute
        result = PipelineDataService.save_pipe_run_data(self.proc_run)

        # Assert
        self.assertIsInstance(result, list)
        mock_pipe_in_plan.objects.filter.assert_called_once_with(plan=self.proc_plan)
        mock_fill.assert_called()
        mock_path.objects.create.assert_called()
        mock_run_pipe_data.objects.create.assert_called()

    def test_save_pipe_run_data_empty_plan(self):
        """Test save_pipe_run_data with no pipes in plan."""
        with patch("processes.services.pipeline_data.PipeInPlan") as mock_pipe_in_plan:
            mock_pipe_in_plan.objects.filter.return_value = []

            result = PipelineDataService.save_pipe_run_data(self.proc_run)

            self.assertEqual(result, [])


class TestRunCreationService(TestCase):
    """Tests for RunCreationService."""

    def setUp(self):
        """Set up test fixtures."""
        self.msi_session = Mock(spec=MsiSession)
        self.msi_session.session_plan = Mock()
        self.msi_session.frames = "/frames/path"

        self.proc_run = Mock(spec=ProcRun)
        self.proc_run.msi_session = self.msi_session
        self.proc_run.created_objects = {}
        self.proc_run.pipes_in_plan = []

    @patch("processes.services.run_creation.Frames")
    def test_create_frames_runpipedata(self, mock_frames):
        """Test create_frames_runpipedata creates Frames record."""
        mock_frames_instance = Mock()
        mock_frames.objects.create.return_value = mock_frames_instance

        result = RunCreationService.create_frames_runpipedata(
            self.proc_run,
            self.msi_session,
        )

        mock_frames.objects.create.assert_called_once()
        mock_frames_instance.save.assert_called_once()
        self.assertEqual(result, mock_frames_instance)

    @patch("processes.services.run_creation.PipeJoint")
    def test_get_pipe_joints(self, mock_pipe_joint):
        """Test get_pipe_joints returns filtered joints."""
        pipe_mock = Mock(spec=Pipe)
        expected_joints = [Mock(), Mock()]
        mock_pipe_joint.objects.filter.return_value = expected_joints

        result = RunCreationService.get_pipe_joints(pipe_mock)

        mock_pipe_joint.objects.filter.assert_called_once_with(pipe_in_plan__pipe=pipe_mock)
        self.assertEqual(result, expected_joints)

    def test_get_input_pipe_pks_no_joints(self):
        """Test get_input_pipe_pks returns [0] when no joints exist."""
        with patch("processes.services.run_creation.PipeJoint") as mock_pipe_joint:
            mock_pipe_joint.objects.filter.return_value = []
            pipe_mock = Mock(spec=Pipe)

            result = RunCreationService.get_input_pipe_pks(self.proc_run, pipe_mock)

            self.assertEqual(result, [0])

    def test_get_input_pipe_pks_with_joints(self):
        """Test get_input_pipe_pks returns unique PKs from joints."""
        with patch("processes.services.run_creation.PipeJoint") as mock_pipe_joint:
            pipe1, pipe2 = Mock(), Mock()
            pipe1.pk, pipe2.pk = 1, 2

            joint1, joint2 = Mock(), Mock()
            joint1.input_pipe_in_plan.pipe = pipe1
            joint2.input_pipe_in_plan.pipe = pipe2

            mock_pipe_joint.objects.filter.return_value = [joint1, joint2]
            pipe_mock = Mock(spec=Pipe)

            result = RunCreationService.get_input_pipe_pks(self.proc_run, pipe_mock)

            self.assertIn(1, result)
            self.assertIn(2, result)

    def test_get_tomo_pipe_no_joints(self):
        """Test get_tomo_pipe returns None when no joints provided."""
        result = RunCreationService.get_tomo_pipe(None)
        self.assertIsNone(result)

    def test_get_tomo_pipe_with_matching_joint(self):
        """Test get_tomo_pipe returns parent pipe for tomogram data types."""
        joint_mock = Mock()
        joint_mock.input_pathtype.static_path.data_type = "rec"
        parent_pipe = Mock(spec=Pipe)
        joint_mock.input_pipe_in_plan.pipe = parent_pipe

        result = RunCreationService.get_tomo_pipe([joint_mock])

        self.assertEqual(result, parent_pipe)

    def test_is_recon_ctf_deconvolved_none_pipe(self):
        """Test is_recon_ctf_deconvolved returns False for None pipe."""
        result = RunCreationService.is_recon_ctf_deconvolved(self.proc_run, None)
        self.assertFalse(result)

    @patch.object(RunCreationService, "get_pipe_joints")
    def test_is_recon_ctf_deconvolved_with_ctf_task(self, mock_get_pipe_joints):
        """Test is_recon_ctf_deconvolved returns True when ctf deconvolution task present."""
        pipe_mock = Mock(spec=Pipe)
        task_mock = Mock()
        task_mock.name = "ctf deconvolution"
        pipe_mock.tasks_performed.all.return_value = [task_mock]
        pipe_mock.output.all.return_value = []
        pipe_mock.input.all.return_value = []
        mock_get_pipe_joints.return_value = []

        result = RunCreationService.is_recon_ctf_deconvolved(self.proc_run, pipe_mock)

        self.assertTrue(result)

    def test_get_pipe_range_with_input_objects(self):
        """Test get_pipe_range calculates correct range with input objects."""
        input_obj_mock = Mock()
        input_obj_mock.pipe_data.pipe.pk = 2
        input_objects = {"tomo": input_obj_mock}
        all_input_pipe_pks = [1, 2, 3, 4]
        pipe_mock = Mock(spec=Pipe)

        result = RunCreationService.get_pipe_range(
            self.proc_run,
            all_input_pipe_pks,
            pipe_mock,
            input_objects,
        )

        # Should return range from index of pk=2 to index+1 (1 to 2, so just [1])
        self.assertEqual(list(result), [1])

    def test_get_pipe_range_no_input_objects(self):
        """Test get_pipe_range defaults to range(0,1) when no input objects."""
        with patch.object(RunCreationService, "get_pipe_joints", return_value=[]):
            all_input_pipe_pks = [1, 2, 3]
            pipe_mock = Mock(spec=Pipe)

            result = RunCreationService.get_pipe_range(
                self.proc_run,
                all_input_pipe_pks,
                pipe_mock,
                {},
            )

            self.assertEqual(list(result), [0])


class TestServiceIntegration(TestCase):
    """Integration tests for services working together."""

    @patch("processes.services.run_creation.RunPipeData")
    @patch("processes.services.run_creation.PipeInPlan")
    def test_create_tomogram_collection_basic_flow(self, mock_pipe_in_plan, mock_run_pipe_data):
        """Test create_tomogram_collection basic execution flow."""
        # Setup
        proc_run = Mock(spec=ProcRun)
        proc_run.msi_session = Mock(spec=MsiSession)
        proc_run.msi_session.session_plan = Mock()
        proc_run.msi_session.frames = "/frames"
        proc_run.pipes_in_plan = []
        proc_run.created_objects = {}

        mock_run_pipe_data.objects.filter.return_value = []

        # Execute
        result = RunCreationService.create_tomogram_collection(proc_run, {})

        # Assert
        self.assertTrue(result)
        self.assertIsInstance(proc_run.created_objects, dict)
