import logging

log = logging.getLogger(__name__)

import argparse
import json
import logging
import os
import time
import uuid
from datetime import datetime

from django.http import HttpRequest
from processes.models import PipeExecution, Review, ReviewTomogram, SyncerLog, SyncerProcess
from tem.models import MsiSession

from common import clusterio
from workflow.views import track_jobs


def generate_uuid():
    return str(uuid.uuid4())


def fix_run_id(run_id):
    """Format run_id to ensure it has 'run' prefix and 3 digits"""
    # Check if run_id already has 'run' prefix
    while run_id.startswith("run"):
        run_id = run_id[3:]
    return f"run{str(int(run_id)).zfill(3)}"


def is_slurm_state_active(state):
    return state in ["PENDING", "CONFIGURING", "RUNNING", "COMPLETING"]


def setup_logging(log_path):
    """Setup logging configuration"""

    os.makedirs(os.path.dirname(log_path), exist_ok=True)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_path),
            logging.StreamHandler(),  # Also print to console
        ],
        force=True,
    )

    log.setLevel(logging.INFO)
    log.info(f"Logging to file: {log_path}")


def check_job_status(job_id):
    """Check if the job is still running"""
    # Create a mock request object
    request = HttpRequest()
    request.method = "GET"
    # Don't specify job_name to get all jobs, then filter by job_id
    request.GET = {}

    # Get job status
    response = track_jobs(request)
    if response.status_code != 200:
        log.error(f"Failed to get job status: {response.status_code}")
        return False

    jobs_data = json.loads(response.content)
    if "jobs" not in jobs_data:
        log.error("No jobs data in response")
        return False

    # Check if job exists and its status
    log.info(f"Checking {len(jobs_data['jobs'])} jobs for job_id: {job_id}")
    for job in jobs_data["jobs"]:
        log.debug(f"Checking job: {job['JOBID']} (looking for {job_id})")
        if job["JOBID"] == job_id:
            status = job["ST"]
            is_running = is_slurm_state_active(job["ST"])
            log.info(f"Job {job_id} status: {status} ({'Running' if is_running else 'Not running'})")

            # Log additional job details
            log.info(f"Job details - Name: {job['NAME']}, User: {job['USER']}, Time: {job['TIME']}")

            return is_running

    log.warning(f"Job {job_id} not found in job list - it may have completed or failed")
    # If job is not found, it might have completed successfully
    # Return False to stop the continuous syncing

    return False


def cleanup_transient_syncer_logs(job_id):
    """Delete sync_start and file_found logs for a completed job.

    These action types are only useful for debugging incomplete syncs.
    Once the syncer completes, any remaining ones would be noise.
    """
    deleted_count = 0
    try:
        deleted_count, _ = SyncerLog.objects.filter(
            job_id=job_id,
            action_type__in=["sync_start", "file_found"],
        ).delete()
        if deleted_count:
            log.info(f"Cleaned up {deleted_count} transient syncer logs for job {job_id}")
    except Exception as e:
        log.warning(f"Failed to clean up syncer logs for job {job_id}: {e}")
    return {"deleted_count": deleted_count}


# TODO: update by grabing by plan, role. Syncer will need the session plan
# The canonical reconstruction FilePattern, seeded by stores/0021. This constant and the
# migration's must match; the row is a code-shipped contract, not free-form config.
REC_PATTERN_LABEL = "{position}_Vol.zarr"


def rec_file_pattern():
    """The FilePattern naming reconstruction volumes. Loud when the row is gone."""
    from django.core.exceptions import ImproperlyConfigured
    from stores.models import FilePattern

    try:
        return FilePattern.objects.get(data_kind__data_type="rec", label=REC_PATTERN_LABEL)
    except FilePattern.DoesNotExist:
        raise ImproperlyConfigured(
            f"FilePattern (rec, {REC_PATTERN_LABEL!r}) is missing -- seeded by stores/0021 and read by "
            f"the syncers and the copick job template. Restore it under Stores → File patterns."
        ) from None


def parse_zarr_filename(filename, pattern=None):
    """The position id in a reconstruction basename, or None when it isn't one.

    Pass `pattern` when calling in a loop -- each default lookup is a query. Replaced
    three divergent hardcoded regexes; this one allows any Position_1_2_3... depth.
    """
    groups = (pattern or rec_file_pattern()).match(filename)
    return groups["position"] if groups else None


def check_zarr_exists(full_path, cluster_id=None):
    """((basename, position_id) pairs, count of .zarr entries seen) for a run directory."""
    # TODO: legacy lister -- replace with clusterio.list_files(full_path,
    # rec_file_pattern().list_glob, include_dirs=True), which also fixes `full_path`
    # being unquoted in the shell command below.
    from processes.services.cluster_resolver import get_default_cluster_id

    cluster_id = cluster_id or get_default_cluster_id()
    found_zarrs = []
    candidates = 0
    pattern = rec_file_pattern()  # once -- the per-file parse below must not query
    ssh = clusterio.get_cluster_ssh_connection(cluster_id=cluster_id)
    stdin, stdout, stderr = ssh.exec_command(f"ls {full_path}")

    # Read the output
    output = stdout.readlines()
    errors = stderr.readlines()

    if errors:
        log.warning("Errors during command execution:")
        for line in errors:
            log.warning(line.strip())

    for line in output:
        line = line.strip()
        # Remove trailing slash if present
        if line.endswith("/"):
            line = line[:-1]

        if line.endswith(".zarr"):
            candidates += 1
            log.info(f"Found ZARR file: {line}")
            position_id = parse_zarr_filename(line, pattern=pattern)
            if position_id:
                found_zarrs.append((line, position_id))
            else:
                log.warning(f"Could not parse position ID from filename: {line}")

    log.info(f"Matched {len(found_zarrs)} of {candidates} .zarr entries in {full_path}")
    return found_zarrs, candidates


class ProcessSyncer(object):
    def __init__(self, base_path, log_dir):
        self.base_path = base_path
        self.log_dir = log_dir
        self.syncer_type = self.__class__.__name__
        self._pipe_execution = None
        self._syncer_process = None
        self.job_id = None
        self.cluster_id = None

    def _log_to_db(self, action_type: str, message: str, metadata: dict = None):
        """Log syncer action to database."""
        try:
            SyncerLog.objects.create(
                pipe_execution=self._pipe_execution,
                job_id=self.job_id,
                action_type=action_type,
                message=message,
                metadata=metadata or {},
                syncer_type=self.syncer_type,
                session_name=getattr(self, "session_name", None),
                run_id=getattr(self, "run_id", None),
            )
        except Exception as e:
            log.warning(f"Failed to write syncer log to DB: {e}")

    def _update_heartbeat(self):
        """Update the syncer process heartbeat."""
        if self._syncer_process:
            try:
                self._syncer_process.save(update_fields=["last_heartbeat"])
            except Exception as e:
                log.warning(f"Failed to update syncer heartbeat: {e}")

    def _mark_syncer_completed(self, status="completed", error_message=None):
        """Mark the syncer process as completed/stopped/failed."""
        if self._syncer_process:
            try:
                from django.utils import timezone

                self._syncer_process.status = status
                self._syncer_process.stopped_at = timezone.now()
                if error_message:
                    self._syncer_process.error_message = error_message
                self._syncer_process.save()
                self._log_to_db("stopped", f"Syncer {status}: {error_message or 'Normal termination'}")
                # Clean up transient logs on successful completion
                if status == "completed" and self.job_id:
                    cleanup = cleanup_transient_syncer_logs(self.job_id)
                    self._log_to_db(
                        "stopped",
                        f"Removed {cleanup['deleted_count']} transient syncer logs for job {self.job_id}",
                    )
            except Exception as e:
                log.warning(f"Failed to mark syncer as {status}: {e}")

    def create_tomogram(self, reconstruction_type, position_id):
        """Create a ReviewTomogram entry in the database"""
        tomogram_id = generate_uuid()

        tomogram = ReviewTomogram.objects.create(
            tomogram_id=tomogram_id,
            session=self.session,
            run_id=self.run_id,
            reconstruction_type=reconstruction_type,
            position_id=position_id,  # Using parsed position_id
            quality="pending",
        )
        log.info(f"Created tomogram: {tomogram_id} with position_id: {position_id}")
        self._log_to_db(
            "tomogram_created",
            f"Created tomogram {position_id} ({reconstruction_type})",
            {
                "tomogram_id": tomogram_id,
                "position_id": position_id,
                "reconstruction_type": reconstruction_type,
            },
        )
        return tomogram

    def update_review_total_counts(self):
        """Update total_count for all reviews associated with this session and run"""

        # Get all reviews for this session and run
        reviews = Review.objects.filter(
            msi_session=self.session,
            run_id=self.run_id,
        )

        for review in reviews:
            old_count = review.total_count

            # Count tomograms for this specific review's reconstruction type
            tomogram_count = ReviewTomogram.objects.filter(
                session=self.session,
                run_id=self.run_id,
                reconstruction_type__iexact=review.reconstruction_type,
            ).count()

            # Update the review's total count
            review.total_count = tomogram_count
            review.save()

            log.info(
                f"Updated review {review.review_id} total_count: {old_count} -> {tomogram_count} (reconstruction_type: {review.reconstruction_type})"
            )

            if old_count != tomogram_count:
                self._log_to_db(
                    "review_updated",
                    f"Updated review count: {old_count} -> {tomogram_count}",
                    {
                        "review_id": str(review.review_id),
                        "reconstruction_type": review.reconstruction_type,
                        "old_count": old_count,
                        "new_count": tomogram_count,
                    },
                )

    def process_zarr_directory(self, recon_type, path_to_zarrs):
        """Sync ReviewTomogram rows of `recon_type` against the .zarr files in `path_to_zarrs`.

        Creates rows for new files; never deletes.
        """
        self._log_to_db(
            "sync_start",
            f"Checking {recon_type} at {path_to_zarrs}",
            {
                "reconstruction_type": recon_type,
                "path": path_to_zarrs,
            },
        )

        found_zarrs, candidates = check_zarr_exists(path_to_zarrs, cluster_id=self.cluster_id)

        unmatched = candidates - len(found_zarrs)
        if unmatched:
            self._log_to_db(
                "warning",
                f"{unmatched} of {candidates} .zarr entries did not match the rec file pattern",
                {
                    "reconstruction_type": recon_type,
                    "candidates": candidates,
                    "unmatched": unmatched,
                },
            )

        if len(found_zarrs) == 0:
            self._log_to_db(
                "sync_complete",
                f"No files found for {recon_type}",
                {
                    "reconstruction_type": recon_type,
                    "count": 0,
                },
            )
            return

        known = dict(
            ReviewTomogram.objects.filter(
                reconstruction_type__iexact=recon_type,
                run_id=self.run_id,
                session=self.session,
            ).values_list("position_id", "tomogram_id")
        )

        seen = set()
        new_count = 0
        for _filename, position_id in found_zarrs:
            if position_id in known:
                seen.add(known[position_id])
            else:
                tomogram = self.create_tomogram(reconstruction_type=recon_type, position_id=position_id)
                if tomogram:
                    new_count += 1
                    seen.add(tomogram.tomogram_id)
                    log.info(f"Created new tomogram for position_id: {position_id}")

        # The directory is re-listed whole every pass, and this will find new ones.
        # missing_files: rows with no file on disk this pass -- reported, never deleted.
        known_count = len(found_zarrs) - new_count
        self._log_to_db(
            "file_found",
            f"Found {new_count} new files ({known_count} previous, {len(found_zarrs)} total) for {recon_type}",
            {
                "reconstruction_type": recon_type,
                "count": len(found_zarrs),
                "new": new_count,
                "previous": known_count,
                "missing_files": len(set(known.values()) - seen),
                "files": [f[0] for f in found_zarrs[:10]],  # First 10 files
            },
        )

    def sync_results(self):
        raise NotImplementedError

    def setup(self, run_id, session_name, cluster_id=None):
        self.run_id = run_id
        self.session_name = session_name
        self.session_path = f"{self.base_path}/{self.session_name}/{self.run_id}"
        self.session = MsiSession.objects.filter(name=self.session_name).first()

        # Look up PipeExecution if job_id is set
        created = False
        if self.job_id:
            self._pipe_execution = PipeExecution.objects.filter(job_id=self.job_id).first()

            # Create or update SyncerProcess record
            self._syncer_process, created = SyncerProcess.objects.update_or_create(
                job_id=self.job_id,
                defaults={
                    "pipe_execution": self._pipe_execution,
                    "syncer_type": self.syncer_type,
                    "session_name": self.session_name,
                    "run_id": self.run_id,
                    "status": "running",
                },
            )

        # Resolve cluster_id: caller-provided wins, else derive from the
        # PipeExecution parameters (canonical source written by
        # workflow.execution.PipeExecutor at submission time).
        if cluster_id:
            self.cluster_id = cluster_id
        elif self._pipe_execution is not None:
            from processes.services.cluster_resolver import cluster_id_from_parameters

            self.cluster_id = cluster_id_from_parameters(self._pipe_execution.parameters)

        # Only log 'init' on first setup (when SyncerProcess is newly created)
        if created:
            self._log_to_db(
                "init",
                f"Syncer started for session={session_name}, run={run_id}",
                {
                    "session_name": session_name,
                    "run_id": run_id,
                    "job_id": self.job_id,
                    "session_path": self.session_path,
                },
            )

    def run(self):
        parser = argparse.ArgumentParser(description=f"{self.syncer_type} results")
        parser.add_argument("--session", help="Session name (e.g., 25apr21a)")
        parser.add_argument("--run", help="Run ID (e.g., run001)")
        parser.add_argument("--continuous", action="store_true", help="Run continuously every minute")
        parser.add_argument("--job-id", help="Job ID to track")
        args = parser.parse_args()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        if args.run and not args.run.startswith("run"):
            parser.error("--run must be in format 'run001' (e.g., run001, run002, etc.)")

        self.job_id = args.job_id

        self.setup(run_id=fix_run_id(args.run), session_name=args.session)
        if not self.session:
            log.error(f"Session {self.session_name} not found")
            return False

        # Setup logging
        log_file = f"{self.syncer_type}_{self.session_name}_{self.run_id}_{timestamp}.log"
        setup_logging(log_path=os.path.join(self.log_dir, log_file))
        log.info(f"args.run: {args.run}")
        if not args.continuous:
            log.info(f"Running {self.syncer_type} once...")
            self.sync_results()
            self._log_to_db("sync_complete", f"{self.syncer_type} single run completed")
            log.info(f"{self.syncer_type} completed successfully")
            self._mark_syncer_completed("completed")
            return True

        log.info(f"Starting {self.syncer_type} service in continuous mode...")
        consecutive_failures = 0
        max_failures = 5  # Maximum number of consecutive failures before stopping
        while True:
            try:
                # Update heartbeat
                self._update_heartbeat()

                # If job_id is provided, check if job is still running
                if args.job_id:
                    job_running = check_job_status(self.job_id)
                    self._log_to_db(
                        "job_check",
                        f"Job {self.job_id} status: {'running' if job_running else 'not running'}",
                        {
                            "job_id": self.job_id,
                            "is_running": job_running,
                        },
                    )
                    if not job_running:
                        log.info(f"Job {self.job_id} is no longer running. Stopping sync service.")
                        self._mark_syncer_completed("completed", "Job completed normally")
                        break

                log.info(f"Running {self.syncer_type}...")
                self.sync_results()
                self._log_to_db("sync_complete", f"{self.syncer_type} cycle completed")
                log.info(f"{self.syncer_type} completed successfully")

                # Reset failure counter on success
                consecutive_failures = 0

                log.info("Waiting 300 seconds before next sync...")
                time.sleep(300)  # Sleep for 300 seconds
            except Exception as e:
                consecutive_failures += 1
                log.error(f"Error in sync cycle: {e}")
                self._log_to_db(
                    "error",
                    f"Error in sync cycle: {str(e)}",
                    {
                        "error": str(e),
                        "consecutive_failures": consecutive_failures,
                    },
                )

                if consecutive_failures >= max_failures:
                    log.error(f"Reached maximum consecutive failures ({max_failures}). Stopping sync service.")
                    self._mark_syncer_completed("failed", f"Maximum failures reached: {str(e)}")
                    break

                log.info(f"Consecutive failures: {consecutive_failures}/{max_failures}")
                log.info("Waiting 60 seconds before retrying...")
                time.sleep(60)
        return True


class JobStatusSyncer:
    """
    Lightweight syncer that tracks job status via sacct.

    Unlike ProcessSyncer subclasses (AretomoSyncer, DenoiseSyncer) that scan for
    output files, this syncer ONLY updates job timing and status information.
    It runs for ALL jobs to ensure accurate completion timestamps.
    """

    syncer_type = "JobStatusSyncer"

    # SLURM state to PipeExecution status mapping
    STATE_MAP = {
        "COMPLETED": "completed",
        "FAILED": "failed",
        "CANCELLED": "cancelled",
        "TIMEOUT": "failed",
        "OUT_OF_MEMORY": "failed",
        "PENDING": "submitted",
        "RUNNING": "running",
        "CONFIGURING": "running",
        "COMPLETING": "running",
    }

    # Terminal states that indicate job has finished
    TERMINAL_STATES = {"COMPLETED", "FAILED", "CANCELLED", "TIMEOUT", "OUT_OF_MEMORY", "NODE_FAIL", "PREEMPTED"}

    def __init__(self, job_id: str, cluster_id: str = "czii"):
        self.job_id = job_id
        self.cluster_id = cluster_id
        self._pipe_execution = None

    def setup(self):
        """Load PipeExecution record and mark syncer as active."""
        self._pipe_execution = PipeExecution.objects.filter(job_id=self.job_id).first()
        if self._pipe_execution and not self._pipe_execution.syncer_active:
            self._pipe_execution.syncer_active = True
            self._pipe_execution.save(update_fields=["syncer_active"])

    def get_job_info_from_sacct(self) -> dict | None:
        """
        Query sacct for job timing and status.

        Returns dict with:
        - state: COMPLETED, FAILED, CANCELLED, RUNNING, PENDING, etc.
        - start_time: datetime or None
        - end_time: datetime or None
        - elapsed: str (e.g., "00:05:30")
        - exit_code: str (e.g., "0:0")

        Returns None if job not found in sacct yet.
        """
        auth = clusterio.get_auth_service_user()

        # Handle hetjob format (e.g., "9238+0" -> "9238")
        base_job_id = self.job_id.split("+")[0]

        cmd = f"sacct -j {base_job_id} --format=JobID,Start,End,Elapsed,State,ExitCode --noheader --parsable2"

        ssh = None
        try:
            ssh = clusterio.get_cluster_ssh_connection(self.cluster_id, auth)
            stdin, stdout, stderr = ssh.exec_command(cmd)
            output = stdout.read().decode("utf-8").strip()

            if not output:
                log.debug(f"Job {self.job_id} not in sacct yet")
                return None

            # Parse output - look for main job line (not .batch or .extern steps)
            lines = output.split("\n")
            for line in lines:
                parts = line.split("|")
                if len(parts) >= 6:
                    job_id_part = parts[0]
                    # Skip batch/extern steps, get main job
                    if "." not in job_id_part:
                        return {
                            "job_id": parts[0],
                            "start_time": self._parse_slurm_time(parts[1]),
                            "end_time": self._parse_slurm_time(parts[2]),
                            "elapsed": parts[3],
                            "state": parts[4].split()[0],  # Handle "CANCELLED by 12345" format
                            "exit_code": parts[5],
                        }

            log.warning(f"Could not parse sacct output for job {self.job_id}: {output}")
            return None

        except Exception as e:
            log.error(f"Error querying sacct for job {self.job_id}: {e}")
            raise
        finally:
            if ssh:
                ssh.close()

    def _parse_slurm_time(self, time_str: str) -> datetime | None:
        """Parse SLURM timestamp format (YYYY-MM-DDTHH:MM:SS)."""
        if not time_str or time_str == "Unknown":
            return None
        try:
            return datetime.strptime(time_str, "%Y-%m-%dT%H:%M:%S")
        except ValueError:
            log.warning(f"Could not parse SLURM time: {time_str}")
            return None

    def update_pipe_execution(self, job_info: dict):
        """Update PipeExecution with accurate timing from sacct."""
        if not self._pipe_execution:
            return

        from django.utils import timezone as dj_timezone

        # Map SLURM state to our status
        slurm_state = job_info.get("state", "")
        new_status = self.STATE_MAP.get(slurm_state, "completed")

        # Only update if status has changed or we have new timing info
        updated_fields = []

        if self._pipe_execution.status != new_status:
            self._pipe_execution.status = new_status
            updated_fields.append("status")
            log.info(f"Job {self.job_id} status updated to: {new_status}")

        # Update started_at if we have it and it's not set
        if job_info.get("start_time") and not self._pipe_execution.started_at:
            # Convert naive datetime to timezone-aware
            start_time = job_info["start_time"]
            if start_time.tzinfo is None:
                start_time = dj_timezone.make_aware(start_time)
            self._pipe_execution.started_at = start_time
            updated_fields.append("started_at")
            log.info(f"Job {self.job_id} started_at set to: {start_time}")

        # Update completed_at and mark syncer inactive if job is in terminal state
        if self.is_job_terminal(job_info):
            if job_info.get("end_time"):
                end_time = job_info["end_time"]
                if end_time.tzinfo is None:
                    end_time = dj_timezone.make_aware(end_time)
                self._pipe_execution.completed_at = end_time
                updated_fields.append("completed_at")
                log.info(f"Job {self.job_id} completed_at set to: {end_time}")

            # Mark syncer as inactive since job has finished
            if self._pipe_execution.syncer_active:
                self._pipe_execution.syncer_active = False
                updated_fields.append("syncer_active")

        if updated_fields:
            self._pipe_execution.save(update_fields=updated_fields)

    def is_job_terminal(self, job_info: dict) -> bool:
        """Check if job has reached a terminal state."""
        state = job_info.get("state", "")
        return state in self.TERMINAL_STATES
