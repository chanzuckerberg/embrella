"""
Tests for processes API views.

Tests the API endpoints moved from umbrella.api_internal to processes.api.views.
"""
import pytest
from django.test import TestCase


pytestmark = pytest.mark.django_db


class TestAPIViewsImport(TestCase):
    """Test that API views are correctly importable and structured."""

    def test_api_views_functions_importable(self):
        """Test that all API view functions are importable."""
        from processes.api.views import (
            export_review_results,
            get_review_tomograms,
            get_tomo_by_msi_session,
        )

        self.assertTrue(callable(get_tomo_by_msi_session))
        self.assertTrue(callable(export_review_results))
        self.assertTrue(callable(get_review_tomograms))

    def test_api_views_classes_importable(self):
        """Test that all API view classes are importable."""
        from processes.api.views import (
            ReviewTomogramView,
            ReviewView,
        )

        # Class-based views
        self.assertTrue(hasattr(ReviewView, 'get'))
        self.assertTrue(hasattr(ReviewView, 'post'))
        self.assertTrue(hasattr(ReviewTomogramView, 'get'))
        self.assertTrue(hasattr(ReviewTomogramView, 'post'))

    def test_api_init_exists(self):
        """Test that API __init__.py module exists."""
        import processes.api
        self.assertTrue(hasattr(processes.api, '__file__'))

    def test_api_views_module_has_docstring(self):
        """Test that API views module has docstring."""
        import processes.api.views
        self.assertIsNotNone(processes.api.views.__doc__)
        self.assertIn('process and review management', processes.api.views.__doc__)
