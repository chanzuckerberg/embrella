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
BASE_PATH = "krios1.processing/aretomo3"
HOST = "10.50.120.90"
PORT = 22
USERNAME = os.getenv('REMOTE_ID')
PASSWORD = os.getenv('REMOTE_PASSWORD')

def generate_uuid():
    return str(uuid.uuid4())

def get_session_path(session_name, run_id, vol_type):
    """Construct session path based on session info and volume type"""
    # Base path
    path = f"{BASE_PATH}/{session_name}/run{run_id}"
    
    # Add volume suffix based on type
    if vol_type == "DCTF":
        path += "/vol001"
    elif vol_type == "SART":
        path += "/vol003"
    
    return path

def parse_zarr_filename(filename):
    # Match both formats: Position_1_2_Vol.zarr or Position_15_Vol.zarr
    match = re.match(r'^Position_(\d+)(?:_(\d+))?_Vol\.zarr$', filename)
    if match:
        if match.group(2):  # If second number exists
            return f"Position_{match.group(1)}_{match.group(2)}"
        else:  # Single number format
            return f"Position_{match.group(1)}"
    return None

def check_zarr_exists(session_name, run_id, vol_type):
    """Check if .zarr file exists for the given session, run, and volume type"""
    try:
        session_path = get_session_path(session_name, run_id, vol_type)
        web_dir_url = urljoin(FILE_SERVER_HOST + "/", session_path + "/")
        print(f"Checking URL: {web_dir_url}")
        
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
                    print(f"Found ZARR file: {filename}")
                    position_id = parse_zarr_filename(filename)
                    if position_id:
                        found_zarrs.append((filename, position_id))
                    else:
                        print(f"❌ Could not parse position ID from filename: {filename}")

        if found_zarrs:
            print(f"Found {len(found_zarrs)} ZARR files in {web_dir_url}")
            return True, found_zarrs
        else:
            print(f"No ZARR files found in {web_dir_url}")
            return False, []

    except requests.RequestException as e:
        print(f"❌ Failed to check ZARR file: {e}")
        return False, []

def create_tomogram(session, run_id, reconstruction_type, position_id):
    """Create a ReviewTomogram entry in the database"""
    try:
        tomogram_id = generate_uuid()
        tomogram = ReviewTomogram.objects.create(
            tomogram_id=tomogram_id,
            session=session,
            run_id=run_id,
            reconstruction_type=reconstruction_type,
            position_id=position_id,  # Using parsed position_id
            quality='pending'
        )
        print(f"✅ Created tomogram: {tomogram_id} with position_id: {position_id}")
        return tomogram
    except Exception as e:
        print(f"❌ Error creating tomogram: {e}")
        return None

def sync_aretomo3_results(session_name=None, run_id=None):
    """Main sync function to be called by cron job"""
    try:
        if not session_name or not run_id:
            print("❌ Session name and run ID are required")
            return
            
        session = MsiSession.objects.filter(name=session_name).first()
        if not session:
            print(f"❌ Session {session_name} not found")
            return
            
        print(f"\nProcessing session: {session.name}, run: {run_id}")
        
        # Track which tomograms we've processed in this run
        processed_tomograms = set()
        
        # Check both SART and DCTF reconstructions
        for recon_type in ["SART", "DCTF"]:
            exists, found_zarrs = check_zarr_exists(session.name, run_id, recon_type)
            if exists and found_zarrs:
                for filename, position_id in found_zarrs:
                    # Check for existing tomogram with same position_id, reconstruction_type, run_id, and session
                    existing_tomogram = ReviewTomogram.objects.filter(
                        position_id=position_id,
                        reconstruction_type=recon_type,
                        run_id=run_id,
                        session=session
                    ).first()
                    
                    if existing_tomogram:
                        print(f"Found existing tomogram with same position_id ({position_id}), reconstruction_type ({recon_type}), run_id ({run_id}), and session ({session.name})")
                        processed_tomograms.add(existing_tomogram.tomogram_id)
                    else:
                        # Create new tomogram
                        tomogram = create_tomogram(session, run_id, recon_type, position_id)
                        if tomogram:
                            processed_tomograms.add(tomogram.tomogram_id)

        # Remove tomograms that no longer exist in the file server
        existing_tomograms = ReviewTomogram.objects.filter(
            session=session,
            run_id=run_id
        )
        for tomogram in existing_tomograms:
            if tomogram.tomogram_id not in processed_tomograms:
                print(f"Removing tomogram that no longer exists: {tomogram.tomogram_id}")
                tomogram.delete()

    except Exception as e:
        print(f"❌ Error in sync_aretomo3_results: {e}")

def check_job_status(job_id):
    """Check if the job is still running"""
    try:
        # Create a mock request object
        request = HttpRequest()
        request.method = 'GET'
        request.GET = {'job_name': job_id}
        
        # Get job status
        response = track_jobs(request)
        if response.status_code != 200:
            return False
            
        jobs_data = json.loads(response.content)
        if 'jobs' not in jobs_data:
            return False
            
        # Check if job exists and its status
        for job in jobs_data['jobs']:
            if job['JOBID'] == job_id:
                # Return True if job is still running (ST is 'R' for running)
                return job['ST'] == 'R'
                
        return False
    except Exception as e:
        print(f"❌ Error checking job status: {e}")
        return False

def main():
    """Main function to run the sync process"""
    try:
        parser = argparse.ArgumentParser(description='Sync AreTomo3 results')
        parser.add_argument('--session', help='Session name (e.g., 25apr21a)')
        parser.add_argument('--run', help='Run ID (e.g., 001)')
        parser.add_argument('--continuous', action='store_true', help='Run continuously every minute')
        parser.add_argument('--job-id', help='Job ID to track')
        args = parser.parse_args()

        if args.continuous:
            print("Starting AreTomo3 sync service in continuous mode...")
            while True:
                try:
                    # If job_id is provided, check if job is still running
                    if args.job_id:
                        if not check_job_status(args.job_id):
                            print(f"Job {args.job_id} is no longer running. Stopping sync service.")
                            break
                    
                    print("\nRunning AreTomo3 sync...")
                    sync_aretomo3_results(args.session, args.run)
                    print("AreTomo3 sync completed successfully")
                    print("Waiting 60 seconds before next sync...")
                    time.sleep(60)  # Sleep for 60 seconds
                except Exception as e:
                    print(f"❌ Error in sync cycle: {str(e)}")
                    print("Waiting 60 seconds before retrying...")
                    time.sleep(60)
        else:
            print("Running AreTomo3 sync once...")
            sync_aretomo3_results(args.session, args.run)
            print("AreTomo3 sync completed successfully")
        
        return True
    except Exception as e:
        print(f"❌ Error in main: {str(e)}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 