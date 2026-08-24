#!/usr/bin/env python
import os
import sys

# Setup Django environment
from pathlib import Path

# Update path calculation for new location (workflow/processors/denoiset/)
BASE_DIR = str(Path(__file__).resolve().parent.parent.parent.parent)
PROJ_DIR = str(Path(BASE_DIR).resolve().parent)
sys.path.append(BASE_DIR)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "umbrella.settings")
sys.path = [p for p in sys.path if p != PROJ_DIR]  # pycharm IDE fix

import django

django.setup()
from processes.models import ReviewTomogram

from workflow import syncers
from workflow.syncers import log


class DenoiseSyncer(syncers.ProcessSyncer):
    def sync_results(self):
        """Main sync function to be called by cron job"""
        log.info(f"Processing session: {self.session.name}, run: {self.run_id}")

        # Track which tomograms we've processed in this run
        processed_tomograms = set()

        # Check for denoise reconstructions
        self.process_zarr_directory(
            recon_type="Denoised",
            path_to_zarrs=self.session_path,
            processed_tomograms=processed_tomograms,
        )

        # Remove tomograms that no longer exist in the file server
        existing_tomograms = ReviewTomogram.objects.filter(
            session=self.session,
            run_id=self.run_id,
            reconstruction_type__iexact="Denoised",  # Case-insensitive comparison
        )
        for tomogram in existing_tomograms:
            if tomogram.tomogram_id not in processed_tomograms:
                log.info(f"Removing tomogram that no longer exists: {tomogram.tomogram_id}")
                tomogram.delete()

        # Update review total counts for this session/run combination
        self.update_review_total_counts()


if __name__ == "__main__":
    from workflow.processors import get_processor

    syncer = DenoiseSyncer(
        base_path=get_processor("denoiset").get_processing_base_path(),
        log_dir=os.path.join(os.path.dirname(__file__), "logs"),
    )
    sys.exit(0 if syncer.run() else 1)
