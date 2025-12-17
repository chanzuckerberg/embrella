"""
Tests for tem API views.

Tests the API endpoints moved from umbrella.api_internal to tem.api.views.
"""
import pytest
from django.test import TestCase


pytestmark = pytest.mark.django_db


class TestAPIViewsImport(TestCase):
    """Test that API views are correctly importable and structured."""

    def test_api_views_importable(self):
        """Test that SessionView is importable."""
        from tem.api.views import SessionView

        self.assertTrue(hasattr(SessionView, 'get'))
        self.assertTrue(hasattr(SessionView, 'get_session_data'))

    def test_session_view_methods_exist(self):
        """Test that SessionView has required methods."""
        from tem.api.views import SessionView

        # Verify SessionView is a class
        self.assertTrue(isinstance(SessionView, type))

        # Verify methods exist
        view = SessionView()
        self.assertTrue(callable(getattr(view, 'get', None)))
        self.assertTrue(callable(getattr(view, 'get_session_data', None)))

    def test_api_init_exists(self):
        """Test that API __init__.py module exists."""
        import tem.api
        self.assertTrue(hasattr(tem.api, '__file__'))

    def test_api_views_module_has_docstring(self):
        """Test that API views module has docstring."""
        import tem.api.views
        self.assertIsNotNone(tem.api.views.__doc__)
        self.assertIn('TEM session management', tem.api.views.__doc__)
