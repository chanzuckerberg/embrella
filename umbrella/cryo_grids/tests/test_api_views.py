"""
Tests for cryo_grids API views.

Tests the API endpoints moved from umbrella.api_internal to cryo_grids.api.views.
"""
import pytest
from django.test import TestCase


pytestmark = pytest.mark.django_db


class TestAPIViewsImport(TestCase):
    """Test that API views are correctly importable and structured."""

    def test_api_views_importable(self):
        """Test that all API view functions are importable."""
        from cryo_grids.api.views import (
            get_available_grids,
            get_grids_by_cassette,
            get_grids_by_user,
        )

        self.assertTrue(callable(get_grids_by_user))
        self.assertTrue(callable(get_available_grids))
        self.assertTrue(callable(get_grids_by_cassette))

    def test_api_init_exists(self):
        """Test that API __init__.py module exists."""
        import cryo_grids.api
        self.assertTrue(hasattr(cryo_grids.api, '__file__'))

    def test_api_views_module_has_docstring(self):
        """Test that API views module has docstring."""
        import cryo_grids.api.views
        self.assertIsNotNone(cryo_grids.api.views.__doc__)
        self.assertIn('cryo-grid management', cryo_grids.api.views.__doc__)
