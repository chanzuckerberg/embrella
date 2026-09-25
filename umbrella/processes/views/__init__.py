"""
Process views module - split into files by concern.

Module Structure:
-----------------
- constants.py: Environment constants and configuration
- filter_views.py: Filter option endpoints
- tomogram_views.py: Tomogram listing
- annotation_views.py: Annotation data management
- directory_views.py: Filesystem survey and directory management

All view functions are re-exported at this level for the URL configuration.
"""

# Annotation views
from .annotation_views import get_annotation_details
from .constants import ENVIRONMENT

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

# Tomogram views
from .tomogram_views import get_tomo_details

__all__ = [
    # Constants and utilities
    "ENVIRONMENT",
    # Filter views
    "available_filters",
    "available_annotation_filter",
    # Tomogram views
    "get_tomo_details",
    # Annotation views
    "get_annotation_details",
    # Directory/Survey views
    "get_surveys",
    "get_directories",
    "get_directory_stats",
    "bulk_update_directory_status",
    "get_directory_filterlist",
    "get_directory_files",
    "get_survey_files",
]
