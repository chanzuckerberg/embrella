#!/usr/bin/env python
import os
import re
import uuid
import requests
import asyncio
import nest_asyncio
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from asgiref.sync import sync_to_async
import django
import sys

# Add the project root directory to Python path
sys.path.append(os.path.abspath('../../'))

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'umbrella.settings')
django.setup()

# Import Django models
from processes.models import ReviewTomogram, Review
from tem.models import MsiSession
from processes.models import ProcRun

# Configuration
FILE_SERVER_HOST = "https://czii-onsite.czbiohub.org"

# Match files like Position_1_2_Vol.zarr
ZARR_FILENAME_PATTERN = re.compile(r'^Position_\d+_\d+_Vol\.zarr$')

# Apply nest_asyncio to allow nested event loops
nest_asyncio.apply()

def generate_uuid():
    return str(uuid.uuid4())

def parse_zarr_filename(filename):
    match = re.match(r'^Position_(\d+)_(\d+)_Vol\.zarr$', filename)
    if match:
        return f"Position_{match.group(1)}_{match.group(2)}"
    return None

def get_session_path(review):
    """Construct session path based on review's reconstruction type and session info"""
    recon_type = review.reconstruction_type.lower()
    session_name = review.session.name
    run_id = review.run_id
    
    # Determine job name based on reconstruction type
    if recon_type in ["dctf", "sart"]:
        job_name = "aretomo3"
    else:  # denoised
        job_name = "denoise"
    
    # Base path
    path = f"krios1.processing/{job_name}/{session_name}/{run_id}"
    
    # Add volume suffix based on reconstruction type
    if recon_type == "dctf":
        path += "/vol001"
    elif recon_type == "sart":
        path += "/vol003"
    # For denoised, no volume suffix needed
    
    return path

def get_zarr_files_from_web(review):
    try:
        session_path = get_session_path(review)
        web_dir_url = urljoin(FILE_SERVER_HOST + "/", session_path + "/")
        print(f"Fetching files from: {web_dir_url}")
        
        response = requests.get(web_dir_url)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')
        file_rows = soup.find_all('tr', class_='file')
        valid_zarr_files = []

        for row in file_rows:
            name_tag = row.find('span', class_='name')
            if name_tag:
                filename = name_tag.text.strip()
                if ZARR_FILENAME_PATTERN.match(filename):
                    valid_zarr_files.append(filename)

        return valid_zarr_files

    except requests.RequestException as e:
        print(f"❌ Failed to fetch ZARR files from web: {e}")
        return []

@sync_to_async
def get_review(review_id):
    """Get review instance by ID"""
    try:
        review = Review.objects.select_related('session').get(review_id=review_id)
        print(f"Found review: {review.review_id}")
        print(f"Session: {review.session.name}")
        print(f"Run ID: {review.run_id}")
        print(f"Reconstruction Type: {review.reconstruction_type}")
        return review
    except Review.DoesNotExist:
        print(f"❌ Review not found with ID: {review_id}")
        raise

@sync_to_async
def get_available_sessions():
    """Get all available sessions with their runs"""
    sessions_data = []
    
    # Get all sessions
    sessions = MsiSession.objects.all().order_by('-created_at')
    
    for session in sessions:
        # Get all runs for this session
        runs = ProcRun.objects.filter(msi_session=session).distinct()
        
        session_runs = []
        for run in runs:
            # Check if this run has any tomograms
            tomograms = ReviewTomogram.objects.filter(
                review__session=session,
                review__run_id=run.name
            ).exists()
            
            if tomograms:
                session_runs.append({
                    "runId": run.name,
                    "reconstructionTypes": ["DCTF", "SART", "Denoised"]  # All types are available
                })
        
        if session_runs:  # Only include sessions that have runs with tomograms
            sessions_data.append({
                "sessionId": str(session.id),
                "sessionName": session.name,
                "createdAt": session.created_at.isoformat() if session.created_at else None,
                "runs": session_runs
            })
    
    return sessions_data

@sync_to_async
def create_tomogram(review, tomogram_id, position_id):
    return ReviewTomogram.objects.create(
        review=review,
        tomogram_id=tomogram_id,
        position_id=position_id,
        quality='',
        rejection_reasons=[],
        object_labels=[]
    )

@sync_to_async
def get_all_tomograms():
    return list(ReviewTomogram.objects.all())

@sync_to_async
def check_tomogram_exists(review, position_id):
    """Check if a tomogram with the given position_id already exists for this review"""
    return ReviewTomogram.objects.filter(
        review=review,
        position_id=position_id
    ).exists()

async def process_files_async(review, zarr_files):
    for filename in zarr_files:
        position_id = parse_zarr_filename(filename)
        if position_id:
            # Check if tomogram already exists
            exists = await check_tomogram_exists(review, position_id)
            if exists:
                print(f"⚠️ Skipping duplicate tomogram for position {position_id}")
                continue
                
            tomogram_id = generate_uuid()
            await create_tomogram(review, tomogram_id, position_id)
            print(f"✅ Created tomogram: {tomogram_id} for position {position_id}")
        else:
            print(f"❌ Skipping invalid filename: {filename}")

async def main_async(review_id):
    # Get review instance
    review = await get_review(review_id)
    
    # Get ZARR files for this review's session
    zarr_files = get_zarr_files_from_web(review)
    print(f"🔍 Found {len(zarr_files)} matching ZARR files")

    await process_files_async(review, zarr_files)

    imported = await get_all_tomograms()
    print(f"\n📊 Total tomograms in DB: {len(imported)}")
    for tomo in imported[:5]:
        print(f"• ID: {tomo.tomogram_id}, Position: {tomo.position_id}")

def main(review_id):
    try:
        asyncio.run(main_async(review_id))
    except RuntimeError as e:
        # If we're already in an event loop (like in Jupyter), use this approach
        loop = asyncio.get_event_loop()
        loop.run_until_complete(main_async(review_id))

if __name__ == "__main__":
    # Example usage: python import_tomograms.py "your-review-id"
    if len(sys.argv) > 1:
        main(sys.argv[1])
    else:
        print("❌ Please provide a review ID as a command line argument")
        sys.exit(1) 