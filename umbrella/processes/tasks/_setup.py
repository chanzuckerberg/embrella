"""
Django setup for worker processes.

This module handles Django initialization for Django-Q2 worker processes.
Import this module before importing any Django models.
"""

import os
import sys
from pathlib import Path

# Django setup for worker processes
BASE_DIR = str(Path(__file__).resolve().parent.parent.parent)
PROJ_DIR = str(Path(BASE_DIR).resolve().parent)
sys.path.append(BASE_DIR)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "umbrella.settings")
sys.path = [p for p in sys.path if p != PROJ_DIR]  # pycharm IDE fix

import django

django.setup()
