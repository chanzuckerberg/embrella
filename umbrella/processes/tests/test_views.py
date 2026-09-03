"""
Tests for processes views (after refactoring into modular structure).
"""

from django.test import SimpleTestCase


class TestModularStructure(SimpleTestCase):
    """Tests to verify the modular view structure is working correctly."""

    def test_views_init_exports_all_functions(self):
        """Test that __init__.py exports all necessary functions."""
        from processes import views

        # Check that key functions are available at package level
        self.assertTrue(hasattr(views, "create_run"))
        self.assertTrue(hasattr(views, "get_tomo_details"))
        self.assertTrue(hasattr(views, "get_session_id"))
        self.assertTrue(hasattr(views, "available_filters"))
        self.assertTrue(hasattr(views, "get_directories"))

    def test_constants_accessible_from_package(self):
        """Test that constants are accessible from processes.views."""
        from processes import views

        self.assertTrue(hasattr(views, "ENVIRONMENT"))

    def test_submodules_exist(self):
        """Test that all view submodules exist and are importable."""
        from processes.views import (
            annotation_views,
            constants,
            directory_views,
            filter_views,
            run_views,
            session_views,
            tomogram_views,
        )

        # Just checking they import without error
        self.assertTrue(hasattr(run_views, "create_run"))
        self.assertTrue(hasattr(tomogram_views, "get_tomo_details"))
        self.assertTrue(hasattr(session_views, "get_session_id"))
        self.assertTrue(hasattr(filter_views, "available_filters"))
        self.assertTrue(hasattr(annotation_views, "get_annotation_details"))
        self.assertTrue(hasattr(directory_views, "get_directories"))
        self.assertTrue(hasattr(constants, "ENVIRONMENT"))
