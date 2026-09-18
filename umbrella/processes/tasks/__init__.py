"""
Django-Q2 async tasks for the processes app.

This package contains async tasks organized by functionality:
- job_tasks: Pipeline execution status monitoring
- syncer_tasks: Output file syncer monitoring
- survey_tasks: Filesystem survey processing

All tasks are re-exported here for backward compatibility with existing
Django-Q task references.
"""

# Job/execution monitoring tasks
from processes.tasks.job_tasks import (
    check_job_status,
)

# Survey tasks
from processes.tasks.survey_tasks import (
    process_survey_results,
    run_survey_status_syncer,
    start_survey_status_syncer,
)

# Syncer tasks
from processes.tasks.syncer_tasks import (
    run_job_status_syncer,
    run_syncer_iteration,
    start_job_status_syncer,
    start_syncer_monitoring,
)

__all__ = [
    # Job tasks
    "check_job_status",
    # Syncer tasks
    "run_syncer_iteration",
    "start_syncer_monitoring",
    "run_job_status_syncer",
    "start_job_status_syncer",
    # Survey tasks
    "run_survey_status_syncer",
    "start_survey_status_syncer",
    "process_survey_results",
]
