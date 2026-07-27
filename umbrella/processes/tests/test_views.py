"""
Tests for processes views (after refactoring into modular structure).
"""

from unittest.mock import patch

from django.test import SimpleTestCase

from processes.views import msi_session_sort_key


class TestConstantsAndUtils(SimpleTestCase):
    """Tests for constants and utility functions."""

    def test_get_base_url_development(self):
        """Test get_base_url returns correct URL for development."""
        with patch("processes.views.constants.ENVIRONMENT", "development"):
            # Need to reload to get new ENVIRONMENT value
            from processes.views.constants import get_base_url as gbu

            url = gbu()
            self.assertIn("localhost", url)

    def test_get_base_url_staging(self):
        """Test get_base_url returns correct URL for staging."""
        with patch("processes.views.constants.ENVIRONMENT", "staging"):
            from processes.views.constants import get_base_url as gbu

            url = gbu()
            self.assertIn("umbrella-dev", url)

    def test_get_base_url_production(self):
        """Test get_base_url returns correct URL for production."""
        with patch("processes.views.constants.ENVIRONMENT", "production"):
            from processes.views.constants import get_base_url as gbu

            url = gbu()
            self.assertIn("umbrella.czbiohub.org", url)

    def test_msi_session_sort_key_valid_format(self):
        """Test msi_session_sort_key with valid session name."""
        # Format: yymmmdda (e.g., 24jan01a)
        key = msi_session_sort_key("24jan01a")

        self.assertIsInstance(key, tuple)
        self.assertEqual(len(key), 4)
        # Should be negative year for descending sort (newer first)
        self.assertEqual(key[0], -24)
        self.assertEqual(key[1], -1)  # January
        self.assertEqual(key[2], -1)  # Day 01
        self.assertEqual(key[3], "a")  # Sequence

    def test_msi_session_sort_key_invalid_format(self):
        """Test msi_session_sort_key with invalid session name."""
        key = msi_session_sort_key("invalid")

        # Should return tuple that sorts to end
        self.assertEqual(key, (0, 0, 0, "z"))

    def test_msi_session_sort_key_december(self):
        """Test msi_session_sort_key with December month."""
        key = msi_session_sort_key("23dec25b")

        self.assertEqual(key[0], -23)
        self.assertEqual(key[1], -12)  # December
        self.assertEqual(key[2], -25)
        self.assertEqual(key[3], "b")


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
        self.assertTrue(hasattr(views, "get_base_url"))
        self.assertTrue(hasattr(views, "base_url"))

    def test_utils_accessible_from_package(self):
        """Test that utils are accessible from processes.views."""
        from processes import views

        self.assertTrue(hasattr(views, "msi_session_sort_key"))

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
            utils,
        )

        # Just checking they import without error
        self.assertTrue(hasattr(run_views, "create_run"))
        self.assertTrue(hasattr(tomogram_views, "get_tomo_details"))
        self.assertTrue(hasattr(session_views, "get_session_id"))
        self.assertTrue(hasattr(filter_views, "available_filters"))
        self.assertTrue(hasattr(annotation_views, "get_annotation_details"))
        self.assertTrue(hasattr(directory_views, "get_directories"))
        self.assertTrue(hasattr(constants, "ENVIRONMENT"))
        self.assertTrue(hasattr(utils, "msi_session_sort_key"))
