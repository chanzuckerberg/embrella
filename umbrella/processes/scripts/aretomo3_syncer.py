#!/usr/bin/env python
import os
import sys

# Setup Django environment
from pathlib import Path

BASE_DIR = str(Path(__file__).resolve().parent.parent.parent)
PROJ_DIR = str(Path(BASE_DIR).resolve().parent)
sys.path.append(BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'umbrella.settings')
sys.path = [p for p in sys.path if p != PROJ_DIR] # pycharm IDE fix

import django

django.setup()
from processes import syncers
from processes.models import ReviewTomogram
from processes.syncers import log


class AretomoSyncer(syncers.ProcessSyncer):
    def sync_results(self):
        """Main sync function to be called by cron job"""
        log.info(f"Processing session: {self.session.name}, run: {self.run_id}")

        # Track which tomograms we've processed in this run
        processed_tomograms = set()

        # Check both SART and DCTF reconstructions
        for recon_type in ["DCTF", "SART"]:
            vol_dir = 'vol001'
            if recon_type == 'SART':
                vol_dir = 'vol003'
            full_path = f"{self.session_path}/{vol_dir}" if vol_dir != '' else self.session_path
            self.process_zarr_directory(recon_type=recon_type,
                                        path_to_zarrs=full_path,
                                        processed_tomograms=processed_tomograms)

        # Remove tomograms that no longer exist in the file server
        existing_tomograms = ReviewTomogram.objects.filter(session=self.session, run_id=self.run_id)
        for tomogram in existing_tomograms:
            if tomogram.tomogram_id not in processed_tomograms:
                log.info(f"Removing tomogram that no longer exists: {tomogram.tomogram_id}")
                tomogram.delete()

        # Update review total counts for this session/run combination
        self.update_review_total_counts()

if __name__ == "__main__":
    syncer = AretomoSyncer(base_path="/hpc/projects/krios1.processing/aretomo3",
                           log_dir=os.path.join(os.path.dirname(__file__), 'logs'))
    sys.exit(0 if syncer.run() else 1)
