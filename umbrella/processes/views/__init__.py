"""
Process views module - refactored into separate files for better organization.

This module serves as the main entry point for all process-related views,
re-exporting functions from specialized submodules for backward compatibility.

Module Structure:
-----------------
- constants.py: Environment constants and configuration
- utils.py: Shared utility functions
- run_views.py: Processing run creation and management
- filter_views.py: Filter option endpoints
- tomogram_views.py: Tomogram syncing and listing
- annotation_views.py: Annotation data management
- session_views.py: MSI session queries
- directory_views.py: Filesystem survey and directory management

All view functions are re-exported at this level to maintain backward
compatibility with existing URL configurations.
"""

# Import and re-export constants and utilities
# Annotation views
from .annotation_views import get_annotation_details
from .constants import ENVIRONMENT, base_url, get_base_url

# Directory/Survey views
from .directory_views import (
    bulk_update_directory_status,
    get_directories,
    get_directory_files,
    get_directory_filterlist,
    get_directory_stats,
    get_survey_files,
    get_surveys,
)

# Filter views
from .filter_views import available_annotation_filter, available_filters

# Import and re-export all view functions from submodules
# Run management views
from .run_views import (
    create_generic_run,
    create_run,
    create_run_post_tomo,
    detail,
    detail_post_tomo,
    reserve_generic_run,
    reserve_run,
    reserve_run_post_tomo,
)

# Session views
from .session_views import get_session_id

# Tomogram views
from .tomogram_views import (
    get_runs,
    get_tomo_details,
    get_tomogram_stats,
    start_sync,
    sync_tomograms_view,
)
from .utils import msi_session_sort_key

# Define __all__ for explicit exports
__all__ = [
    # Constants and utilities
    "ENVIRONMENT",
    "base_url",
    "get_base_url",
    "msi_session_sort_key",
    # Run views
    "detail",
    "reserve_run",
    "create_run",
    "reserve_generic_run",
    "create_generic_run",
    "detail_post_tomo",
    "reserve_run_post_tomo",
    "create_run_post_tomo",
    # Filter views
    "available_filters",
    "available_annotation_filter",
    # Tomogram views
    "get_tomo_details",
    "sync_tomograms_view",
    "get_runs",
    "get_tomogram_stats",
    "start_sync",
    # Annotation views
    "get_annotation_details",
    # Session views
    "get_session_id",
    # Directory/Survey views
    "get_surveys",
    "get_directories",
    "get_directory_stats",
    "bulk_update_directory_status",
    "get_directory_filterlist",
    "get_directory_files",
    "get_survey_files",
]
