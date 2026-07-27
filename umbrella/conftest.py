"""
Pytest configuration for Django tests.

This file ensures Django is configured before any test modules are imported,
which is necessary because test files import Django models at the module level.
"""

import os

# Force SQLite for tests (override USE_MYSQL if set)
os.environ["USE_MYSQL"] = "False"

# Set the settings module before importing anything else
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "umbrella.settings")

import django

# Ensure Django is set up before test collection
django.setup()
