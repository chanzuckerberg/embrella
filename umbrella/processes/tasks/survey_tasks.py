"""
Django-Q2 async tasks for filesystem survey processing.
"""

import os
import tempfile
from datetime import UTC, datetime

from django.utils import timezone
from django_q.tasks import async_task
from umbrella_logger import logger

from common import clusterio
from processes.tasks._setup import *  # noqa: F401,F403 - Django setup


def run_survey_status_syncer(survey_id: int, cluster_id: str = "czii"):
    """
    Single iteration of filesystem survey status syncer.

    Queries SLURM's sacct for the survey job status and updates the
    FilesystemSurvey record. When the job completes successfully,
    triggers the result processing task.

    This task is run by a Schedule that polls every minute. The schedule
    is automatically deleted when the job reaches a terminal state.

    Args:
        survey_id: FilesystemSurvey ID to track
        cluster_id: Cluster to query (czii or bruno)

    Returns:
        dict with status and survey_id
    """
    from django_q.models import Schedule
    from workflow.syncers import JobStatusSyncer

    from processes.models import FilesystemSurvey

    # Helper to clean up schedule when done
    def stop_schedule():
        Schedule.objects.filter(name=f"survey_status_{survey_id}").delete()

    try:
        survey = FilesystemSurvey.objects.get(id=survey_id)
    except FilesystemSurvey.DoesNotExist:
        logger.error(f"FilesystemSurvey {survey_id} not found")
        stop_schedule()
        return {"status": "error", "survey_id": survey_id, "error": "Survey not found"}

    # Check if survey is already in terminal state (prevents duplicate processing)
    if survey.status in ["completed", "failed", "processing"]:
        logger.debug(f"Survey {survey_id} already in terminal state: {survey.status}")
        stop_schedule()
        return {"status": "already_done", "survey_id": survey_id, "survey_status": survey.status}

    if not survey.job_id:
        logger.error(f"FilesystemSurvey {survey_id} has no job_id")
        stop_schedule()
        return {"status": "error", "survey_id": survey_id, "error": "No job ID"}

    # Create a JobStatusSyncer to query sacct
    syncer = JobStatusSyncer(job_id=survey.job_id, cluster_id=cluster_id)

    try:
        # Initialize SSH connection
        syncer.setup()

        job_info = syncer.get_job_info_from_sacct()

        if job_info is None:
            # Job not in sacct yet (just submitted) - wait for next scheduled run
            logger.debug(f"Survey job {survey.job_id} not in sacct yet, waiting...")
            return {"status": "waiting", "survey_id": survey_id}

        # Update survey status based on job state
        state = job_info.get("state", "").upper()

        if state in ["RUNNING", "CONFIGURING"]:
            if survey.status != "running":
                survey.status = "running"
                survey.started_at = timezone.now()
                survey.save(update_fields=["status", "started_at", "updated_at"])
                logger.info(f"Survey {survey_id} is now running")

        if syncer.is_job_terminal(job_info):
            # Job finished - stop the schedule
            stop_schedule()

            if state == "COMPLETED":
                survey.status = "processing"
                survey.completed_at = timezone.now()
                survey.save(update_fields=["status", "completed_at", "updated_at"])

                logger.info(f"Survey job {survey.job_id} completed. Starting result processing...")

                # Trigger result processing
                async_task(
                    "processes.tasks.process_survey_results",
                    survey_id,
                    cluster_id,
                    task_name=f"process_survey_{survey_id}",
                    timeout=3600,  # 1 hour timeout for processing
                )

                return {
                    "status": "processing",
                    "survey_id": survey_id,
                    "job_state": state,
                }

            else:
                # Job failed or was cancelled
                survey.status = "failed"
                survey.completed_at = timezone.now()
                survey.error_message = f"SLURM job ended with state: {state}"
                survey.save(update_fields=["status", "completed_at", "error_message", "updated_at"])

                logger.error(f"Survey job {survey.job_id} failed with state: {state}")

                return {
                    "status": "failed",
                    "survey_id": survey_id,
                    "job_state": state,
                }

        # Job still running - wait for next scheduled run
        logger.debug(f"Survey job {survey.job_id} still {state}, waiting for next poll...")
        return {"status": "running", "survey_id": survey_id, "job_state": state}

    except Exception as e:
        logger.error(f"Error in survey status syncer for {survey_id}: {e}")
        # Don't stop schedule on error - let it retry
        return {"status": "error", "survey_id": survey_id, "error": str(e)}


def start_survey_status_syncer(survey_id: int, cluster_id: str = "czii"):
    """
    Start the survey status syncer for a newly submitted survey job.

    Creates a Schedule that polls sacct every minute until the survey job
    completes. The schedule is automatically deleted when the job reaches
    a terminal state.

    Args:
        survey_id: FilesystemSurvey ID to track
        cluster_id: Cluster to query (czii or bruno)

    Returns:
        str: Django-Q schedule name
    """
    from django_q.models import Schedule

    schedule_name = f"survey_status_{survey_id}"

    # Delete any existing schedule for this survey (prevents duplicates)
    Schedule.objects.filter(name=schedule_name).delete()

    # Create a schedule that runs every minute
    # Note: args must be a valid Python literal for ast.literal_eval()
    schedule = Schedule.objects.create(
        name=schedule_name,
        func="processes.tasks.run_survey_status_syncer",
        args=repr((survey_id, cluster_id)),  # e.g. "(1, 'czii')"
        schedule_type=Schedule.MINUTES,
        minutes=1,
        repeats=-1,  # Run indefinitely until deleted
    )

    logger.info(
        f"Started survey status syncer schedule for survey {survey_id} on {cluster_id}. Schedule ID: {schedule.id}",
    )

    # Also run immediately once
    async_task(
        "processes.tasks.run_survey_status_syncer",
        survey_id,
        cluster_id,
        task_name=f"survey_status_{survey_id}_initial",
    )

    return schedule_name


def process_survey_results(survey_id: int, cluster_id: str = "czii"):
    """
    Process the Parquet file from a completed filesystem survey.

    Reads the Parquet file via SFTP, computes directory-level aggregates,
    and creates DirectorySummary records in the database. Also computes
    origin detection (app_generated, user_created, synced_from_czii).

    Args:
        survey_id: FilesystemSurvey ID
        cluster_id: Cluster where the Parquet file is located

    Returns:
        dict with processing results
    """
    import duckdb

    from processes.models import DirectorySummary, FilesystemSurvey
    from processes.services.domain_path_service import DomainPathService

    try:
        survey = FilesystemSurvey.objects.get(id=survey_id)
    except FilesystemSurvey.DoesNotExist:
        logger.error(f"FilesystemSurvey {survey_id} not found")
        return {"status": "error", "survey_id": survey_id, "error": "Survey not found"}

    if not survey.results_parquet_path:
        survey.status = "failed"
        survey.error_message = "No Parquet path set"
        survey.save(update_fields=["status", "error_message", "updated_at"])
        return {"status": "error", "survey_id": survey_id, "error": "No Parquet path"}

    logger.info(f"Processing survey {survey_id} results from {survey.results_parquet_path}")

    try:
        # Read Parquet file via SFTP
        auth = {
            "username": os.getenv("SLURM_USER"),
            "key_filename": os.getenv("SLURM_KEYFILE"),
        }

        ssh = clusterio.get_cluster_ssh_connection(cluster_id=cluster_id, auth=auth)

        try:
            sftp = ssh.open_sftp()

            # Download Parquet file to temp location
            with tempfile.NamedTemporaryFile(suffix=".parquet", delete=False) as tmp:
                tmp_path = tmp.name

            sftp.get(survey.results_parquet_path, tmp_path)
            sftp.close()

            logger.info(f"Downloaded Parquet file to {tmp_path}")

            # Query with DuckDB
            con = duckdb.connect()

            # Get total statistics
            stats = con.execute(f"""
                SELECT
                    COUNT(*) FILTER (WHERE type = 'file') as total_files,
                    COUNT(*) FILTER (WHERE type = 'directory') as total_directories,
                    SUM(size) as total_size
                FROM read_parquet('{tmp_path}')
            """).fetchone()

            survey.total_files = stats[0] or 0
            survey.total_directories = stats[1] or 0
            survey.total_size_bytes = stats[2] or 0

            logger.info(
                f"Survey {survey_id}: {survey.total_files} files, "
                f"{survey.total_directories} directories, "
                f"{survey.total_size_bytes / (1024**3):.2f} GB total",
            )

            # Get size/count by user (username from parquet)
            user_stats = con.execute(f"""
                SELECT
                    username,
                    SUM(size) as total_size,
                    COUNT(*) as file_count
                FROM read_parquet('{tmp_path}')
                WHERE type IN ('file', 'zarr')
                GROUP BY username
            """).fetchall()

            survey.size_by_user = {str(row[0]): row[1] for row in user_stats}
            survey.count_by_user = {str(row[0]): row[2] for row in user_stats}

            # Compute directory-level aggregates
            # Get unique parent directories with their aggregates
            dir_aggregates = con.execute(f"""
                SELECT
                    regexp_replace(path, '/[^/]+$', '') as parent_dir,
                    COUNT(*) as file_count,
                    SUM(size) as total_size,
                    MODE(uid) as common_uid,
                    MODE(username) as common_username,
                    MAX(mtime) as newest_mtime,
                    MIN(mtime) as oldest_mtime
                FROM read_parquet('{tmp_path}')
                WHERE type IN ('file', 'zarr')
                  AND path != parent_dir
                GROUP BY parent_dir
                HAVING parent_dir IS NOT NULL AND parent_dir != ''
            """).fetchall()

            logger.info(f"Found {len(dir_aggregates)} directories to summarize")

            # Get entity paths for origin detection and entity linking
            entity_paths = DomainPathService.get_all_entity_paths()

            # Create DirectorySummary records
            summaries_created = 0
            base_path_depth = len(survey.base_path.rstrip("/").split("/"))

            for row in dir_aggregates:
                parent_dir, file_count, total_size, common_uid, common_username, newest_mtime, oldest_mtime = row

                if not parent_dir:
                    continue

                # Calculate depth relative to base_path
                dir_depth = len(parent_dir.rstrip("/").split("/")) - base_path_depth

                # Detect origin and get entity link info
                origin = "user_created"  # Default
                content_type_id = None
                object_id = None

                if parent_dir in entity_paths:
                    origin = "app_generated"
                    entity_info = entity_paths[parent_dir]
                    content_type_id = entity_info["content_type_id"]
                    object_id = entity_info["object_id"]
                elif cluster_id == "bruno":
                    # For bruno, check if path exists on czii (synced)
                    # This would require comparing against a czii survey
                    # For now, we'll leave it as user_created and enhance later
                    pass

                # Create or update DirectorySummary
                DirectorySummary.objects.update_or_create(
                    survey=survey,
                    path=parent_dir,
                    defaults={
                        "cluster": cluster_id,
                        "file_count": file_count,
                        "total_size_bytes": total_size or 0,
                        "owner_uid": common_uid,
                        "owner_username": common_username,
                        "origin": origin,
                        "depth": max(0, dir_depth),
                        "content_type_id": content_type_id,
                        "object_id": object_id,
                        "newest_file_mtime": (datetime.fromtimestamp(newest_mtime, tz=UTC) if newest_mtime else None),
                        "oldest_file_mtime": (datetime.fromtimestamp(oldest_mtime, tz=UTC) if oldest_mtime else None),
                    },
                )
                summaries_created += 1

                if summaries_created % 1000 == 0:
                    logger.info(f"Created {summaries_created} directory summaries...")

            con.close()

            # Cleanup temp file
            os.unlink(tmp_path)

            # Update survey status
            survey.status = "completed"
            survey.save()

            logger.info(
                f"Survey {survey_id} processing complete. Created {summaries_created} directory summaries.",
            )

            return {
                "status": "completed",
                "survey_id": survey_id,
                "total_files": survey.total_files,
                "total_directories": survey.total_directories,
                "total_size_bytes": survey.total_size_bytes,
                "summaries_created": summaries_created,
            }

        finally:
            ssh.close()

    except Exception as e:
        logger.error(f"Error processing survey {survey_id}: {e}", exc_info=True)
        survey.status = "failed"
        survey.error_message = str(e)
        survey.save(update_fields=["status", "error_message", "updated_at"])
        return {"status": "error", "survey_id": survey_id, "error": str(e)}
