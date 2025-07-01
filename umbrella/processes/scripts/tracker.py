import requests
from bs4 import BeautifulSoup
import re

# session_run_pairs = [
#     ('25mar25a', 'run001'),
#     ('25mar12a', 'run002'),
#     ('25apr15f', 'run001'),
#     ('25apr16b', 'run001'),
#     ('25jun02a', 'run001'),
#     ('25mar28b', 'run001'),
#     ('25mar31a', 'run001'),
#     ('25apr14c', 'run001'),
#     ('25feb13c', 'run003'),
#     ('25mar13a', 'run001'),
#     ('25mar19a', 'run001'),
#     ('25mar25c', 'run002'),
#     ('25apr18a', 'run001'),
#     ('25mar26b', 'run001'),
#     ('25feb24b', 'run002'),
#     ('25feb26b', 'run001'),
#     ('25feb27a', 'run001'),
#     ('25feb28a', 'run001'),
#     ('25feb28b', 'run001'),
#     ('25feb28c', 'run001'),
#     ('25feb28e', 'run002'),
#     ('25mar10a', 'run001')
# ]

session_run_pairs = [
    ('25jun12a', 'run001'),
    ('25jun13a', 'run001'),
    ('25jun16a', 'run001'),
    ('25jun16a', 'run002'),
    ('25jun17a', 'run001'),
    ('25jun17a', 'run002'),
    ('25jun25a', 'run001'),
    ('25jun30a', 'run001'),  # Assuming run001 as run not specified
    ('25jun30b', 'run001'),
    ('25jun30b', 'run002'),
]

# Base URL prefix common to all your paths
BASE_URL_PREFIX = "https://czii-onsite.czbiohub.org/krios1.processing/aretomo3/"

def get_directory_contents(url):
    """
    Fetches the content of a directory URL and returns a list of files/directories' hrefs.
    This function assumes the server provides an HTML directory listing.
    It returns the href attribute values directly as they appear in the HTML.

    Args:
        url (str): The URL of the directory to fetch.

    Returns:
        list: A list of strings, where each string is the href of a link found
              in the directory listing (e.g., 'file.mrc', 'vol001/').
              Returns an empty list if there's an error.
    """
    try:
        response = requests.get(url, timeout=10) # Add a timeout
        response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)

        soup = BeautifulSoup(response.text, 'html.parser')
        contents = []
        
        # Look for <a> tags within the HTML
        for a_tag in soup.find_all('a'):
            href = a_tag.get('href')
            if href:
                # Exclude the parent directory link typically named '../'
                if href == '../':
                    continue
                contents.append(href)
        return contents
    except requests.exceptions.Timeout:
        return []
    except requests.exceptions.ConnectionError:
        return []
    except requests.exceptions.RequestException as e:
        return []

def check_vol_files_and_zarr_directories(vol_num):
    """
    Iterates through the session_run_pairs, constructs URLs, and checks for
    Vol.mrc files and their corresponding Vol.zarr directories, specifically
    within the 'vol003/' subdirectory.
    Only prints information about missing Vol.zarr directories and provides a summary.
    """
    print("Starting consistency check for Vol.mrc and Vol.zarr directories (targeting vol003/ specifically)...\n")
    print("--- Listing only MISSING corresponding Vol.zarr directories ---\n")

    mismatch_occurred_in_pairs = set() # To store (session, run) pairs that had at least one mismatch

    for session, run in session_run_pairs:
        # Construct the URL for the specific vol003 directory within the current session and run
        # THIS IS THE KEY CHANGE: TARGETING vol003/
        vol003_url = f"{BASE_URL_PREFIX}{session}/{run}/{vol_num}"
        
        vol_contents = get_directory_contents(vol003_url)

        # Check for access/content issues before proceeding
        if not vol_contents:
            try:
                # Attempt to get status code if contents are empty to distinguish between 
                # inaccessible URL and simply no files.
                status_code = requests.get(vol003_url, timeout=5).status_code
                if status_code != 200:
                    print(f"❌ Session: {session}, Run: {run} - URL inaccessible ({status_code}): {vol003_url}")
                    mismatch_occurred_in_pairs.add((session, run))
            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError, requests.exceptions.RequestException):
                 print(f"❌ Session: {session}, Run: {run} - Connection/Timeout error accessing: {vol003_url}")
                 mismatch_occurred_in_pairs.add((session, run))
            continue # Move to the next session/run pair

        # Filter for .mrc files, excluding those with 'EVN' or 'ODD'
        mrc_files = [
            f_href for f_href in vol_contents
            if f_href.endswith('.mrc') and "EVN" not in f_href and "ODD" not in f_href
        ]
        
        if not mrc_files:
            # No relevant MRC files, so no Zarrs to check for. Skip silently.
            continue

        # Process each relevant .mrc file
        for mrc_file_href in mrc_files:
            base_name = mrc_file_href[:-4] 
            expected_zarr_dir_href = f"{base_name}.zarr/"
            
            if expected_zarr_dir_href not in vol_contents:
                print(f"❌ Session: {session}, Run: {run} - Missing: '{expected_zarr_dir_href}' for '{mrc_file_href}' in {vol003_url}")
                mismatch_occurred_in_pairs.add((session, run))
    
    print("\n" + "=" * 80)
    print("Consistency check complete.")
    
    if mismatch_occurred_in_pairs:
        print("\nSummary of Session/Run IDs with Mismatches:")
        for session, run in sorted(list(mismatch_occurred_in_pairs)):
            print(f"- Session: {session}, Run: {run}")
    else:
        print("✅ No mismatches found for any of the specified session/run pairs.")
    print("=" * 80)

if __name__ == "__main__":
    check_vol_files_and_zarr_directories("vol003")