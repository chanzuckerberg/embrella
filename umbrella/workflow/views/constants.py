"""
Module-level constants for workflow views.

This module contains all configuration constants, paths, and mappings
used across the workflow application.
"""

import os

# Celery Configuration
CELERY_BEAT_SCHEDULE = {
    "update_job_data_cache_every_5_seconds": {
        "task": "workflow.tasks.update_job_data_cache",
        "schedule": 5.0,  # every 5 seconds
    },
}

# Directory and Path Constants
# Go up three levels: views/ -> workflow/ -> umbrella/
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DENOISET_TEMPLATE_PATH = os.path.join(BASE_DIR, "workflow", "legacy/denoiset_template.sh")
DENOISET_SCRIPT_PATH = "/hpc/projects/group.czii/krios1.processing/denoise/scripts"
STATUS_CHECKER_TEMPLATE_PATH = os.path.join(BASE_DIR, "workflow", "legacy/status_checker.sh")
STATUS_CHECKER_SCRIPT_PATH = "/hpc/projects/group.czii/krios1.processing/software/scripts"
ARETOMO3_TEMPLATE_PATH = os.path.join(BASE_DIR, "workflow", "templates", "workflows", "aretomo3_advanced_template.sh")
ARETOMO3_BASIC_TEMPLATE_PATH = os.path.join(
    BASE_DIR, "workflow", "templates", "workflows", "aretomo3_basic_template.sh"
)
ARETOMO3_SCRIPT_PATH = "/hpc/projects/group.czii/krios1.processing/aretomo3/scripts"
COPICK_SCRIPT_DIR = "/hpc/projects/group.czii/krios1.processing/copick/scripts"
COPICK_TEMPLATE_PATH = os.path.join(BASE_DIR, "workflow", "legacy/copick_create_template.sh")
COPICK_IMPORT_TOMO_TEMPLATE_PATH = os.path.join(BASE_DIR, "workflow", "legacy/copick_import_tomo_template.sh")
COPICK_ADD_OBJECT_TEMPLATE_PATH = os.path.join(BASE_DIR, "workflow", "legacy/copick_add_object_template.sh")

# AreTomo3 Parameter Keys
KEYS = (
    "PixSize",
    "SplitSum",
    "Resume",
    "EerSampling",
    "McPatch",
    "Cmd",
    "McIter",
    "Group",
    "RotGain",
    "FlipGain",
    "InvGain",
    "TotalDose",
    "AlignZ",
    "VolZ",
    "ExtZ",
    "AtBin",
    "TiltAxis",
    "TiltCor",
    "AtPatch",
    "OutImod",
    "ExtPhase",
    "CorrCTF",
    "McBin",
    "Wbp",
)

# SSH Connection Configuration
HOST = "10.50.120.90"
HOST_BRUNO = "192.168.98.229"
PORT = 22
USERNAME = os.getenv("SLURM_USER")
KEYFILE = os.getenv("SLURM_KEYFILE")

# Environment Configuration
ENVIRONMENT = os.getenv("DJANGO_ENV", "development")

# Cluster Configuration
DEFAULT_CLUSTER_ID = "czii"

# Remote Paths
METADATA_SUMMARY_PATH = "/hpc/projects/group.czii/krios1.processing/aretomo3/"
DATA_COLLECTION_PATH = "/hpc/instruments/czii.krios1/OffloadData/"
HOSTNAME = "https://czii-onsite.czbiohub.org/krios1.processing/aretomo3/"
ARETOMO3_PROCESSING_PATH = "/hpc/projects/group.czii/krios1.processing/aretomo3/"

# SLURM Status Mappings
SLURM_STATE_TO_LABEL = {
    "RUNNING": "Running",
    "PENDING": "Pending",
    "COMPLETING": "Completing",
    "COMPLETED": "Completed",
    "FAILED": "Failed",
    "CANCELLED": "Cancelled",
    "TIMEOUT": "Timeout",
}

# Reverse mapping: label to SLURM state
LABEL_TO_SLURM_STATE = {v: k for k, v in SLURM_STATE_TO_LABEL.items()}
