#!/usr/bin/env python
import os
import re
import uuid
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import django
import sys
import argparse
import time
import json
import logging
from datetime import datetime

# Add the project root directory to Python path
sys.path.append(os.path.abspath('../../'))

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'umbrella.settings')
django.setup()

# Import Django models
from processes.models import ReviewTomogram, Review
from tem.models import MsiSession
from processes.models import ProcRun
from workflow.views import track_jobs, format_job_output
from django.http import HttpRequest

# Configuration
FILE_SERVER_HOST = "https://czii-onsite.czbiohub.org"
BASE_PATH = "krios1.processing/denoise"
HOST = "10.50.120.90"
PORT = 22
USERNAME = os.getenv('REMOTE_ID')
PASSWORD = os.getenv('REMOTE_PASSWORD')

def generate_uuid():
    return str(uuid.uuid4())

def get_session_path(session_name, run_id):
    """Construct session path for denoise processing"""
    # Remove 'run' prefix if it exists for the file path
    run_id_clean = run_id[3:] if run_id.startswith('run') else run_id
    return f"{BASE_PATH}/{session_name}/run{run_id_clean}/"

def parse_zarr_filename(filename):
    # Match both formats: Position_1_2_Vol.zarr or Position_15_Vol.zarr
    match = re.match(r'^Position_(\d+)(?:_(\d+))?_Vol\.zarr$', filename)
    if match:
        if match.group(2):  # If second number exists
            return f"Position_{match.group(1)}_{match.group(2)}"
        else:  # Single number format
            return f"Position_{match.group(1)}"
    return None

def check_zarr_exists(session_name, run_id):
    """Check if .zarr file exists for the given session and run"""
    try:
        session_path = get_session_path(session_name, run_id)
        web_dir_url = urljoin(FILE_SERVER_HOST + "/", session_path + "/")
        logging.info(f"Checking URL: {web_dir_url}")
        
        response = requests.get(web_dir_url)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')
        file_rows = soup.find_all('tr', class_='file')
        
        found_zarrs = []
        for row in file_rows:
            name_tag = row.find('span', class_='name')
            if name_tag:
                filename = name_tag.text.strip()
                # Remove trailing slash if present
                if filename.endswith('/'):
                    filename = filename[:-1]
                
                if filename.endswith('.zarr'):
                    logging.info(f"Found ZARR file: {filename}")
                    position_id = parse_zarr_filename(filename)
                    if position_id:
                        found_zarrs.append((filename, position_id))
                    else:
                        logging.warning(f"Could not parse position ID from filename: {filename}")

        if found_zarrs:
            logging.info(f"Found {len(found_zarrs)} ZARR files in {web_dir_url}")
            return True, found_zarrs
        else:
            logging.info(f"No ZARR files found in {web_dir_url}")
            return False, []

    except requests.RequestException as e:
        logging.error(f"Failed to check ZARR file: {e}")
        return False, []

def create_tomogram(session, run_id, position_id):
    """Create a ReviewTomogram entry in the database for denoise processing"""
    try:
        tomogram_id = generate_uuid()
        # Ensure run_id has 'run' prefix
        run_id_formatted = f"run{run_id}" if not run_id.startswith('run') else run_id
        
        tomogram = ReviewTomogram.objects.create(
            tomogram_id=tomogram_id,
            session=session,
            run_id=run_id_formatted,  # Use formatted run_id with 'run' prefix
            reconstruction_type="Denoised",  # Fixed reconstruction type for denoise
            position_id=position_id,
            quality='pending'
        )
        logging.info(f"Created tomogram: {tomogram_id} with position_id: {position_id}")
        return tomogram
    except Exception as e:
        logging.error(f"Error creating tomogram: {e}")
        return None

def setup_logging(session_name, run_id):
    """Setup logging configuration"""
    # Create logs directory if it doesn't exist
    log_dir = os.path.join(os.path.dirname(__file__), 'logs')
    os.makedirs(log_dir, exist_ok=True)
    
    # Create log filename with timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_file = os.path.join(log_dir, f'denoise_sync_{session_name}_{run_id}_{timestamp}.log')
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()  # Also print to console
        ]
    )
    
    logging.info(f"Logging to file: {log_file}")
    return log_file

def check_job_status(job_id):
    """Check if the job is still running"""
    try:
        # Create a mock request object
        request = HttpRequest()
        request.method = 'GET'
        # Don't specify job_name to get all jobs, then filter by job_id
        request.GET = {}
        
        # Get job status
        response = track_jobs(request)
        if response.status_code != 200:
            logging.error(f"Failed to get job status: {response.status_code}")
            return False
            
        jobs_data = json.loads(response.content)
        if 'jobs' not in jobs_data:
            logging.error("No jobs data in response")
            return False
            
        # Check if job exists and its status
        for job in jobs_data['jobs']:
            if job['JOBID'] == job_id:
                is_running = job['ST'] == 'R'
                logging.info(f"Job {job_id} status: {'Running' if is_running else 'Not running'}")
                return is_running
                
        logging.warning(f"Job {job_id} not found in job list - it may have completed or failed")
        # If job is not found, it might have completed successfully
        # Return False to stop the continuous syncing
        return False
    except Exception as e:
        logging.error(f"Error checking job status: {e}")
        return False

def sync_denoise_results(session_name=None, run_id=None):
    """Main sync function to be called by cron job"""
    try:
        if not session_name or not run_id:
            logging.error("Session name and run ID are required")
            return
            
        session = MsiSession.objects.filter(name=session_name).first()
        if not session:
            logging.error(f"Session {session_name} not found")
            return
            
        logging.info(f"Processing session: {session.name}, run: {run_id}")
        
        # Track which tomograms we've processed in this run
        processed_tomograms = set()
        
        # Check for denoise reconstructions
        exists, found_zarrs = check_zarr_exists(session.name, run_id)
        if exists and found_zarrs:
            for filename, position_id in found_zarrs:
                # Ensure run_id has 'run' prefix for database query
                run_id_formatted = f"run{run_id}" if not run_id.startswith('run') else run_id
                
                # Check for existing tomogram with same position_id, run_id, session, and reconstruction_type (case-insensitive)
                existing_tomogram = ReviewTomogram.objects.filter(
                    position_id=position_id,
                    reconstruction_type__iexact="Denoised",  # Case-insensitive comparison
                    run_id=run_id_formatted,
                    session=session
                ).first()
                
                if existing_tomogram:
                    logging.info(f"Skipping duplicate tomogram - Found existing record with position_id ({position_id}), run_id ({run_id_formatted}), session ({session.name}), and reconstruction_type ({existing_tomogram.reconstruction_type})")
                    processed_tomograms.add(existing_tomogram.tomogram_id)
                else:
                    # Create new tomogram only if no duplicate exists
                    tomogram = create_tomogram(session, run_id, position_id)
                    if tomogram:
                        processed_tomograms.add(tomogram.tomogram_id)
                        logging.info(f"Created new tomogram for position_id: {position_id}")

        # Remove tomograms that no longer exist in the file server
        # Ensure run_id has 'run' prefix for database query
        run_id_formatted = f"run{run_id}" if not run_id.startswith('run') else run_id
        existing_tomograms = ReviewTomogram.objects.filter(
            session=session,
            run_id=run_id_formatted,
            reconstruction_type__iexact="Denoised"  # Case-insensitive comparison
        )
        for tomogram in existing_tomograms:
            if tomogram.tomogram_id not in processed_tomograms:
                logging.info(f"Removing tomogram that no longer exists: {tomogram.tomogram_id}")
                tomogram.delete()

        # Update review total counts for this session/run combination
        update_review_total_counts(session, run_id_formatted)

    except Exception as e:
        logging.error(f"Error in sync_denoise_results: {e}")

def update_review_total_counts(session, run_id):
    """Update total_count for all reviews associated with this session and run"""
    try:
        from processes.models import Review
        
        # Get all reviews for this session and run
        reviews = Review.objects.filter(
            msi_session=session,
            run_id=run_id
        )
        
        for review in reviews:
            # Count tomograms for this specific review's reconstruction type
            tomogram_count = ReviewTomogram.objects.filter(
                session=session,
                run_id=run_id,
                reconstruction_type__iexact=review.reconstruction_type
            ).count()
            
            # Update the review's total count
            old_count = review.total_count
            review.total_count = tomogram_count
            review.save()
            
            logging.info(f"Updated review {review.review_id} total_count: {old_count} -> {tomogram_count} (reconstruction_type: {review.reconstruction_type})")
            
    except Exception as e:
        logging.error(f"Error updating review total counts: {e}")

def main():
    """Main function to run the sync process"""
    try:
        parser = argparse.ArgumentParser(description='Sync Denoise results')
        parser.add_argument('--session', help='Session name (e.g., 25apr21a)')
        parser.add_argument('--run', help='Run ID (e.g., 001)')
        parser.add_argument('--continuous', action='store_true', help='Run continuously every minute')
        parser.add_argument('--job-id', help='Job ID to track')
        args = parser.parse_args()

        # Setup logging
        log_file = setup_logging(args.session, args.run)
        logging.info(f"Starting Denoise sync script with args: {args}")

        if args.continuous:
            logging.info("Starting Denoise sync service in continuous mode...")
            while True:
                try:
                    # If job_id is provided, check if job is still running
                    if args.job_id:
                        if not check_job_status(args.job_id):
                            logging.info(f"Job {args.job_id} is no longer running. Stopping sync service.")
                            break
                    
                    logging.info("Running Denoise sync...")
                    sync_denoise_results(args.session, args.run)
                    logging.info("Denoise sync completed successfully")
                    logging.info("Waiting 60 seconds before next sync...")
                    time.sleep(60)  # Sleep for 60 seconds
                except Exception as e:
                    logging.error(f"Error in sync cycle: {e}")
                    logging.info("Waiting 60 seconds before retrying...")
                    time.sleep(60)
        else:
            logging.info("Running Denoise sync once...")
            sync_denoise_results(args.session, args.run)
            logging.info("Denoise sync completed successfully")
        
        return True
    except Exception as e:
        logging.error(f"Error in main: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 