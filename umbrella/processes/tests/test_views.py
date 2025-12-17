"""
Tests for processes views (after refactoring into modular structure).
"""
import pytest
from django.test import TestCase, RequestFactory
from django.contrib.auth.models import User
from unittest.mock import Mock, patch, MagicMock

from processes.views import (
    # Run views
    create_run,
    reserve_run,
    create_generic_run,
    reserve_generic_run,
    # Tomogram views
    get_tomo_details,
    get_runs,
    get_tomogram_stats,
    # Session views
    get_session_id,
    # Filter views
    available_filters,
    available_annotation_filter,
    # Data management views
    get_processing_data_list,
    get_storage_stats,
    bulk_update_status,
    # Constants and utils
    get_base_url,
    msi_session_sort_key,
)


pytestmark = pytest.mark.django_db


class TestViewsImports(TestCase):
    """Test that all views are correctly importable from processes.views."""

    def test_run_views_imported(self):
        """Test run view functions are importable."""
        self.assertTrue(callable(create_run))
        self.assertTrue(callable(reserve_run))
        self.assertTrue(callable(create_generic_run))
        self.assertTrue(callable(reserve_generic_run))

    def test_tomogram_views_imported(self):
        """Test tomogram view functions are importable."""
        self.assertTrue(callable(get_tomo_details))
        self.assertTrue(callable(get_runs))
        self.assertTrue(callable(get_tomogram_stats))

    def test_session_views_imported(self):
        """Test session view functions are importable."""
        self.assertTrue(callable(get_session_id))

    def test_filter_views_imported(self):
        """Test filter view functions are importable."""
        self.assertTrue(callable(available_filters))
        self.assertTrue(callable(available_annotation_filter))

    def test_data_management_views_imported(self):
        """Test data management view functions are importable."""
        self.assertTrue(callable(get_processing_data_list))
        self.assertTrue(callable(get_storage_stats))
        self.assertTrue(callable(bulk_update_status))

    def test_constants_and_utils_imported(self):
        """Test constants and utilities are importable."""
        self.assertTrue(callable(get_base_url))
        self.assertTrue(callable(msi_session_sort_key))


class TestConstantsAndUtils(TestCase):
    """Tests for constants and utility functions."""

    def test_get_base_url_development(self):
        """Test get_base_url returns correct URL for development."""
        with patch('processes.views.constants.ENVIRONMENT', 'development'):
            # Need to reload to get new ENVIRONMENT value
            from processes.views.constants import get_base_url as gbu
            url = gbu()
            self.assertIn('localhost', url)

    def test_get_base_url_staging(self):
        """Test get_base_url returns correct URL for staging."""
        with patch('processes.views.constants.ENVIRONMENT', 'staging'):
            from processes.views.constants import get_base_url as gbu
            url = gbu()
            self.assertIn('umbrella-dev', url)

    def test_get_base_url_production(self):
        """Test get_base_url returns correct URL for production."""
        with patch('processes.views.constants.ENVIRONMENT', 'production'):
            from processes.views.constants import get_base_url as gbu
            url = gbu()
            self.assertIn('umbrella.czbiohub.org', url)

    def test_msi_session_sort_key_valid_format(self):
        """Test msi_session_sort_key with valid session name."""
        # Format: yymmmdda (e.g., 24jan01a)
        key = msi_session_sort_key('24jan01a')

        self.assertIsInstance(key, tuple)
        self.assertEqual(len(key), 4)
        # Should be negative year for descending sort (newer first)
        self.assertEqual(key[0], -24)
        self.assertEqual(key[1], -1)  # January
        self.assertEqual(key[2], -1)  # Day 01
        self.assertEqual(key[3], 'a')  # Sequence

    def test_msi_session_sort_key_invalid_format(self):
        """Test msi_session_sort_key with invalid session name."""
        key = msi_session_sort_key('invalid')

        # Should return tuple that sorts to end
        self.assertEqual(key, (0, 0, 0, 'z'))

    def test_msi_session_sort_key_december(self):
        """Test msi_session_sort_key with December month."""
        key = msi_session_sort_key('23dec25b')

        self.assertEqual(key[0], -23)
        self.assertEqual(key[1], -12)  # December
        self.assertEqual(key[2], -25)
        self.assertEqual(key[3], 'b')


class TestRunViews(TestCase):
    """Tests for run view functions."""

    def setUp(self):
        """Set up test fixtures."""
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass',
        )

    @patch('processes.views.run_views.MsiSession')
    @patch('processes.views.run_views.ProcPlan')
    @patch('processes.views.run_views.ProcRun')
    def test_create_run_success(self, mock_proc_run, mock_proc_plan, mock_msi_session):
        """Test create_run successfully creates a run."""
        # Setup
        request = self.factory.post('/processes/create', {
            'proc_plan': 1,
            'msi_session': 1,
        }, content_type='application/json')
        request.user = self.user

        mock_session = Mock()
        mock_plan = Mock()
        mock_run_instance = Mock()
        mock_run_instance.id = 1

        mock_msi_session.objects.get.return_value = mock_session
        mock_proc_plan.objects.get.return_value = mock_plan
        mock_proc_run.objects.create.return_value = mock_run_instance

        # Execute
        response = create_run(request)

        # Assert
        self.assertEqual(response.status_code, 302)  # Redirect
        mock_run_instance.save.assert_called()
        mock_run_instance.save_pipe_run_data.assert_called()
        mock_run_instance.create_tomogram_collection.assert_called()


class TestSessionViews(TestCase):
    """Tests for session view functions."""

    def setUp(self):
        """Set up test fixtures."""
        self.factory = RequestFactory()

    @patch('processes.views.session_views.MsiSession')
    def test_get_session_id_found(self, mock_msi_session):
        """Test get_session_id returns session ID when found."""
        # Setup
        request = self.factory.get('/api/get-session-id?session_name=24jan01a')

        mock_session = Mock()
        mock_session.id = 42
        mock_msi_session.objects.get.return_value = mock_session

        # Execute
        response = get_session_id(request)

        # Assert
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['session_id'], 42)

    @patch('processes.views.session_views.MsiSession')
    def test_get_session_id_not_found(self, mock_msi_session):
        """Test get_session_id returns 404 when session not found."""
        # Setup
        request = self.factory.get('/api/get-session-id?session_name=nonexistent')

        mock_msi_session.objects.get.side_effect = mock_msi_session.DoesNotExist

        # Execute
        response = get_session_id(request)

        # Assert
        self.assertEqual(response.status_code, 404)


class TestFilterViews(TestCase):
    """Tests for filter view functions."""

    def setUp(self):
        """Set up test fixtures."""
        self.factory = RequestFactory()

    @patch('processes.views.filter_views.ProcPlan')
    @patch('processes.views.filter_views.MsiSession')
    def test_available_filters_basic(self, mock_msi_session, mock_proc_plan):
        """Test available_filters returns filter options."""
        # Setup
        request = self.factory.get('/v1/filterlist/')

        mock_proc_plan.objects.all.return_value = []
        mock_msi_session.objects.all.return_value = []

        # Execute
        response = available_filters(request)

        # Assert
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('filters', data)


class TestModularStructure(TestCase):
    """Tests to verify the modular view structure is working correctly."""

    def test_views_init_exports_all_functions(self):
        """Test that __init__.py exports all necessary functions."""
        from processes import views

        # Check that key functions are available at package level
        self.assertTrue(hasattr(views, 'create_run'))
        self.assertTrue(hasattr(views, 'get_tomo_details'))
        self.assertTrue(hasattr(views, 'get_session_id'))
        self.assertTrue(hasattr(views, 'available_filters'))
        self.assertTrue(hasattr(views, 'get_processing_data_list'))

    def test_constants_accessible_from_package(self):
        """Test that constants are accessible from processes.views."""
        from processes import views

        self.assertTrue(hasattr(views, 'ENVIRONMENT'))
        self.assertTrue(hasattr(views, 'get_base_url'))
        self.assertTrue(hasattr(views, 'base_url'))

    def test_utils_accessible_from_package(self):
        """Test that utils are accessible from processes.views."""
        from processes import views

        self.assertTrue(hasattr(views, 'msi_session_sort_key'))

    def test_submodules_exist(self):
        """Test that all view submodules exist and are importable."""
        from processes.views import run_views, tomogram_views, session_views, filter_views
        from processes.views import annotation_views, data_management_views, constants, utils

        # Just checking they import without error
        self.assertTrue(hasattr(run_views, 'create_run'))
        self.assertTrue(hasattr(tomogram_views, 'get_tomo_details'))
        self.assertTrue(hasattr(session_views, 'get_session_id'))
        self.assertTrue(hasattr(filter_views, 'available_filters'))
        self.assertTrue(hasattr(annotation_views, 'get_annotation_details'))
        self.assertTrue(hasattr(data_management_views, 'get_processing_data_list'))
        self.assertTrue(hasattr(constants, 'ENVIRONMENT'))
        self.assertTrue(hasattr(utils, 'msi_session_sort_key'))
