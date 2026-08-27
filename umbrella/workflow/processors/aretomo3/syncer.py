#!/usr/bin/env python
import os
import sys

# Setup Django environment
from pathlib import Path

# Update path calculation for new location (workflow/processors/aretomo3/)
BASE_DIR = str(Path(__file__).resolve().parent.parent.parent.parent)
PROJ_DIR = str(Path(BASE_DIR).resolve().parent)
sys.path.append(BASE_DIR)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "umbrella.settings")
sys.path = [p for p in sys.path if p != PROJ_DIR]  # pycharm IDE fix

import django

django.setup()

from workflow import syncers
from workflow.syncers import log


class AretomoSyncer(syncers.ProcessSyncer):
    def sync_results(self):
        """Main sync function to be called by cron job"""
        log.info(f"Processing session: {self.session.name}, run: {self.run_id}")

        # Check both SART and DCTF reconstructions. A pass only ever creates rows --
        # see ProcessSyncer.process_zarr_directory on why sync never deletes.
        recon_type_to_vol_dir = {
            "DCTF": "vol001",
            "SART": "vol003",
        }
        for recon_type in ["DCTF", "SART"]:
            vol_dir = recon_type_to_vol_dir[recon_type]
            full_path = f"{self.session_path}/{vol_dir}" if vol_dir != "" else self.session_path
            self.process_zarr_directory(recon_type=recon_type, path_to_zarrs=full_path)

        # Update review total counts for this session/run combination
        self.update_review_total_counts()


if __name__ == "__main__":
    # spawned by trigger_syncer / job_api with --session/--run, or run by hand for a one-off re-sync.
    import argparse

    from workflow.processors import get_processor

    parser = argparse.ArgumentParser()
    parser.add_argument("--scope", help="Microscope.name, optional")
    parser.add_argument("--session", help="msi session name")
    args, _ = parser.parse_known_args()

    scope = args.scope or syncers.scope_for_session(args.session or "")
    if not scope:
        parser.error("--scope is required when --session is missing or unknown")

    syncer = AretomoSyncer(
        base_path=get_processor("aretomo3").get_processing_base_path(scope=scope),
        log_dir=os.path.join(os.path.dirname(__file__), "logs"),
    )
    sys.exit(0 if syncer.run() else 1)
