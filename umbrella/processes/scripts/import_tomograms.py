#!/usr/bin/env python
import os
import re
import uuid
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
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

# Match files like Position_1_2_Vol.zarr or Position_15_Vol.zarr
ZARR_FILENAME_PATTERN = re.compile(r'^Position_\d+(?:_\d+)?_Vol\.zarr$')

def generate_uuid():
    return str(uuid.uuid4())

def parse_zarr_filename(filename):
    # Match both formats: Position_1_2_Vol.zarr or Position_15_Vol.zarr
    match = re.match(r'^Position_(\d+)(?:_(\d+))?_Vol\.zarr$', filename)
    if match:
        if match.group(2):  # If second number exists
            return f"Position_{match.group(1)}_{match.group(2)}"
        else:  # Single number format
            return f"Position_{match.group(1)}"
    return None

def get_session_path(review):
    """Construct session path based on review's reconstruction type and session info"""
    recon_type = review.reconstruction_type.lower()
    session_name = review.msi_session.name
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

        print(f"Found {len(file_rows)} total files in directory")
        
        for row in file_rows:
            name_tag = row.find('span', class_='name')
            if name_tag:
                filename = name_tag.text.strip()
                # Remove trailing slash if present
                if filename.endswith('/'):
                    filename = filename[:-1]
                
                print(f"Processing file: {filename}")
                # Check if it matches the ZARR pattern
                if ZARR_FILENAME_PATTERN.match(filename):
                    valid_zarr_files.append(filename)
                    print(f"✅ Found valid ZARR file: {filename}")
                else:
                    print(f"❌ Skipping non-matching file: {filename}")

        print(f"Total valid ZARR files found: {len(valid_zarr_files)}")
        return valid_zarr_files

    except requests.RequestException as e:
        print(f"❌ Failed to fetch ZARR files from web: {e}")
        return []

def get_review(review_id):
    """Get review instance by ID"""
    try:
        review = Review.objects.select_related('msi_session').get(review_id=review_id)
        print(f"Found review: {review.review_id}")
        print(f"Session: {review.msi_session.name}")
        print(f"Run ID: {review.run_id}")
        print(f"Reconstruction Type: {review.reconstruction_type}")
        return review
    except Review.DoesNotExist:
        print(f"❌ Review not found with ID: {review_id}")
        raise

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
                review__msi_session=session,
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

def create_tomogram(review, tomogram_id, position_id):
    # Determine reconstruction type based on the path
    session_path = get_session_path(review)
    if "vol003" in session_path:
        recon_type = "SART"
    elif "vol001" in session_path:
        recon_type = "DCTF"
    else:
        recon_type = "Denoised"

    return ReviewTomogram.objects.create(
        review=review,
        tomogram_id=tomogram_id,
        position_id=position_id,
        run_id=review.run_id,
        reconstruction_type=recon_type,
        session_id=review.msi_session.id,
        quality='pending',
        rejection_reasons=[],
        object_labels=[]
    )

def get_all_tomograms():
    return list(ReviewTomogram.objects.all())

def check_tomogram_exists(review, position_id):
    """Check if a tomogram with the given position_id already exists for this review"""
    return ReviewTomogram.objects.filter(
        review=review,
        position_id=position_id
    ).exists()

def process_files(review, zarr_files, existing_positions=None):
    """Process ZARR files and create tomograms, skipping existing ones"""
    print(f"\nProcessing {len(zarr_files)} ZARR files...")
    print(f"Existing positions to skip: {existing_positions}")
    
    created_count = 0
    skipped_count = 0
    
    for filename in zarr_files:
        position_id = parse_zarr_filename(filename)
        if position_id:
            # Skip if position already exists
            if existing_positions and position_id in existing_positions:
                print(f"⚠️ Skipping existing tomogram for position {position_id}")
                skipped_count += 1
                continue
                
            # Check if tomogram already exists in database
            exists = check_tomogram_exists(review, position_id)
            if exists:
                print(f"⚠️ Skipping duplicate tomogram for position {position_id}")
                skipped_count += 1
                continue
                
            tomogram_id = generate_uuid()
            create_tomogram(review, tomogram_id, position_id)
            print(f"✅ Created tomogram: {tomogram_id} for position {position_id}")
            created_count += 1
        else:
            print(f"❌ Skipping invalid filename: {filename}")
            skipped_count += 1
    
    print(f"\nProcessing complete:")
    print(f"• Created: {created_count} tomograms")
    print(f"• Skipped: {skipped_count} files")
    print(f"• Total processed: {len(zarr_files)} files")

def main(review_id, existing_positions=None):
    """Main function to run the import process"""
    try:
        print(f"\nStarting import process for review_id: {review_id}")
        print(f"Existing positions to skip: {existing_positions}")
        
        # Get review instance
        review = get_review(review_id)
        
        # Get ZARR files for this review's session
        zarr_files = get_zarr_files_from_web(review)
        print(f"🔍 Found {len(zarr_files)} matching ZARR files")

        # Process files, passing existing positions to skip
        process_files(review, zarr_files, existing_positions)

        # Update review counts
        total_count = ReviewTomogram.objects.filter(review=review).count()
        reviewed_count = ReviewTomogram.objects.filter(
            review=review,
            quality__in=['accepted', 'rejected', 'uncertain', 'exemplary']
        ).count()
        
        # Update the review record
        review.total_count = total_count
        review.reviewed_count = reviewed_count
        review.save()
        
        print(f"\n📊 Updated review counts:")
        print(f"• Total tomograms: {total_count}")
        print(f"• Reviewed tomograms: {reviewed_count}")

        imported = get_all_tomograms()
        print(f"\n📊 Total tomograms in DB: {len(imported)}")
        for tomo in imported[:5]:
            print(f"• ID: {tomo.tomogram_id}, Position: {tomo.position_id}")
            
    except Exception as e:
        print(f"❌ Error in main: {str(e)}")
        raise

if __name__ == "__main__":
    # Example usage: python import_tomograms.py "your-review-id"
    if len(sys.argv) > 1:
        main(sys.argv[1])
    else:
        print("❌ Please provide a review ID as a command line argument")
        sys.exit(1) 