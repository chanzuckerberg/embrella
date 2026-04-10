"""
Management command to delete transient syncer logs for completed jobs.

Removes sync_start and file_found log entries that are no longer needed
for debugging. These are cleaned up automatically on job completion, but
this command handles historical data and edge cases (crashes, deploys).

Usage:
    python manage.py cleanup_syncer_logs --dry-run         # Preview deletion count
    python manage.py cleanup_syncer_logs                   # Delete all for completed jobs
    python manage.py cleanup_syncer_logs --job-id 12345    # Specific job
"""

from django.core.management.base import BaseCommand
from umbrella_logger import logger

from processes.models import SyncerLog, SyncerProcess

TRANSIENT_ACTION_TYPES = ["sync_start", "file_found"]
BATCH_SIZE = 10_000


class Command(BaseCommand):
    help = "Delete transient syncer logs (sync_start, file_found) for completed jobs."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show how many logs would be deleted without deleting them.",
        )
        parser.add_argument(
            "--job-id",
            type=str,
            help="Only clean up logs for a specific job ID.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        job_id = options.get("job_id")

        qs = SyncerLog.objects.filter(action_type__in=TRANSIENT_ACTION_TYPES)

        if job_id:
            qs = qs.filter(job_id=job_id)
        else:
            # Only clean up logs for jobs whose syncer has completed
            completed_job_ids = SyncerProcess.objects.filter(
                status="completed",
            ).values_list("job_id", flat=True)
            qs = qs.filter(job_id__in=completed_job_ids)

        total_count = qs.count()

        if dry_run:
            self.stdout.write(f"Would delete {total_count} transient syncer logs.")
            return

        if total_count == 0:
            self.stdout.write("No transient syncer logs to delete.")
            return

        # Batch delete to avoid long table locks
        deleted_total = 0
        while True:
            batch_ids = list(qs.values_list("id", flat=True)[:BATCH_SIZE])
            if not batch_ids:
                break
            deleted_count, _ = SyncerLog.objects.filter(id__in=batch_ids).delete()
            deleted_total += deleted_count
            logger.info(f"Deleted batch of {deleted_count} syncer logs ({deleted_total}/{total_count})")

        self.stdout.write(self.style.SUCCESS(f"Deleted {deleted_total} transient syncer logs."))
