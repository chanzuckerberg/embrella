import logging

log = logging.getLogger(__name__)

import argparse
import json
import logging
import os
import re
import time
import uuid
from datetime import datetime

from django.http import HttpRequest
from processes.models import Review, ReviewTomogram
from tem.models import MsiSession
from workflow.views import track_jobs

from common import clusterio


def generate_uuid():
    return str(uuid.uuid4())

def fix_run_id(run_id):
    """Format run_id to ensure it has 'run' prefix and 3 digits"""
    # Check if run_id already has 'run' prefix
    while run_id.startswith("run"):
        run_id = run_id[3:]
    return f"run{str(int(run_id)).zfill(3)}"

def is_slurm_state_active(state):
    return state in ['PENDING', 'CONFIGURING', 'RUNNING', 'COMPLETING']

def setup_logging(log_path):
    """Setup logging configuration"""

    os.makedirs(os.path.dirname(log_path), exist_ok=True)

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
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
    request.method = 'GET'
    # Don't specify job_name to get all jobs, then filter by job_id
    request.GET = {}

    # Get job status
    response = track_jobs(request)
    if response.status_code != 200:
        log.error(f"Failed to get job status: {response.status_code}")
        return False

    jobs_data = json.loads(response.content)
    if 'jobs' not in jobs_data:
        log.error("No jobs data in response")
        return False

    # Check if job exists and its status
    log.info(f"Checking {len(jobs_data['jobs'])} jobs for job_id: {job_id}")
    for job in jobs_data['jobs']:
        log.debug(f"Checking job: {job['JOBID']} (looking for {job_id})")
        if job['JOBID'] == job_id:
            status = job['ST']
            is_running = is_slurm_state_active(job['ST'])
            log.info(f"Job {job_id} status: {status} ({'Running' if is_running else 'Not running'})")

            # Log additional job details
            log.info(f"Job details - Name: {job['NAME']}, User: {job['USER']}, Time: {job['TIME']}")

            return is_running

    log.warning(f"Job {job_id} not found in job list - it may have completed or failed")
    # If job is not found, it might have completed successfully
    # Return False to stop the continuous syncing

    return False

def parse_zarr_filename(filename):
    # Match both formats: Position_1_2_Vol.zarr or Position_15_Vol.zarr
    match = re.match(r'^Position_(\d+)(?:_(\d+))?_Vol\.zarr$', filename)
    if match:
        if match.group(2):  # If second number exists
            return f"Position_{match.group(1)}_{match.group(2)}"
        else:  # Single number format
            return f"Position_{match.group(1)}"
    return None

def check_zarr_exists(full_path):
    found_zarrs = []
    ssh = clusterio.get_cluster_ssh_connection(cluster_id='czii')
    stdin, stdout, stderr = ssh.exec_command(f'ls {full_path}')

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
        if line.endswith('/'):
            line = line[:-1]

        if line.endswith('.zarr'):
            log.info(f"Found ZARR file: {line}")
            position_id = parse_zarr_filename(line)
            if position_id:
                found_zarrs.append((line, position_id))
            else:
                log.warning(f"Could not parse position ID from filename: {line}")

    log.info(f"Found {len(found_zarrs)} ZARR files in {full_path}")
    return found_zarrs

class ProcessSyncer(object):
    def __init__(self, base_path, log_dir):
        self.base_path = base_path
        self.log_dir = log_dir
        self.syncer_type = self.__class__.__name__

    def create_tomogram(self, reconstruction_type, position_id):
        """Create a ReviewTomogram entry in the database"""
        tomogram_id = generate_uuid()

        tomogram = ReviewTomogram.objects.create(
            tomogram_id=tomogram_id,
            session=self.session,
            run_id=self.run_id,
            reconstruction_type=reconstruction_type,
            position_id=position_id,  # Using parsed position_id
            quality='pending',
        )
        print(f"Created tomogram: {tomogram_id} with position_id: {position_id}")
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
                f"Updated review {review.review_id} total_count: {old_count} -> {tomogram_count} (reconstruction_type: {review.reconstruction_type})")

    def process_zarr_directory(self, recon_type, path_to_zarrs, processed_tomograms=set()):
        """Check remote directory path_to_zarrsm and create reviewtomogram objects for them if not present."""
        found_zarrs = check_zarr_exists(path_to_zarrs)
        if len(found_zarrs) > 0:
            for _filename, position_id in found_zarrs:
                # Check for existing tomogram with same position_id, reconstruction_type, run_id, and session
                existing_tomogram = ReviewTomogram.objects.filter(
                    position_id=position_id,
                    reconstruction_type=recon_type,
                    run_id=self.run_id,
                    session=self.session,
                ).first()

                if existing_tomogram:
                    log.info(
                        f"Found existing tomogram with same position_id ({position_id}), reconstruction_type ({recon_type}), run_id ({self.run_id}), and session ({self.session.name})")
                    processed_tomograms.add(existing_tomogram.tomogram_id)
                else:
                    # Create new tomogram
                    tomogram = self.create_tomogram(reconstruction_type=recon_type, position_id=position_id)
                    if tomogram:
                        processed_tomograms.add(tomogram.tomogram_id)
                        log.info(f"Created new tomogram for position_id: {position_id}")

        return processed_tomograms

    def sync_results(self):
        raise NotImplementedError

    def setup(self, run_id, session_name):
        self.run_id = run_id
        self.session_name = session_name
        self.session_path = f"{self.base_path}/{self.session_name}/{self.run_id}"
        self.session = MsiSession.objects.filter(name=self.session_name).first()

    def run(self):
        parser = argparse.ArgumentParser(description=f'{self.syncer_type} results')
        parser.add_argument('--session', help='Session name (e.g., 25apr21a)')
        parser.add_argument('--run', help='Run ID (e.g., run001)')
        parser.add_argument('--continuous', action='store_true', help='Run continuously every minute')
        parser.add_argument('--job-id', help='Job ID to track')
        args = parser.parse_args()
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        if args.run and not args.run.startswith('run'):
            parser.error("--run must be in format 'run001' (e.g., run001, run002, etc.)")

        self.job_id = args.job_id

        self.setup(run_id=fix_run_id(args.run), session_name=args.session)
        if not self.session:
            log.error(f"Session {self.session_name} not found")
            return False

        # Setup logging
        log_file = f'{self.syncer_type}_{self.session_name}_{self.run_id}_{timestamp}.log'
        setup_logging(log_path=os.path.join(self.log_dir, log_file))
        log.info(f"args.run: {args.run}")
        if not args.continuous:
            log.info(f"Running {self.syncer_type} once...")
            self.sync_results()
            log.info(f"{self.syncer_type} completed successfully")
            return True

        log.info(f"Starting {self.syncer_type} service in continuous mode...")
        consecutive_failures = 0
        max_failures = 5  # Maximum number of consecutive failures before stopping
        while True:
            try:
                # If job_id is provided, check if job is still running
                if args.job_id:
                    if not check_job_status(self.job_id):
                        log.info(f"Job {self.job_id} is no longer running. Stopping sync service.")
                        break

                log.info(f"Running {self.syncer_type}...")
                self.sync_results()
                log.info(f"{self.syncer_type} completed successfully")

                # Reset failure counter on success
                consecutive_failures = 0

                log.info("Waiting 300 seconds before next sync...")
                time.sleep(300)  # Sleep for 300 seconds
            except Exception as e:
                consecutive_failures += 1
                log.error(f"Error in sync cycle: {e}")

                if consecutive_failures >= max_failures:
                    log.error(f"Reached maximum consecutive failures ({max_failures}). Stopping sync service.")
                    break

                log.info(f"Consecutive failures: {consecutive_failures}/{max_failures}")
                log.info("Waiting 60 seconds before retrying...")
                time.sleep(60)
        return True
