"""
Django management command to fetch logs for completed SLURM jobs.

This command queries for PipeExecution records where:
- status = 'completed'
- logs_fetched_at is NULL (logs haven't been fetched yet)

For each execution, it fetches stdout/stderr logs from the cluster
and stores them in the database.

Usage:
    python manage.py fetch_completed_job_logs

    # Limit number of jobs to process
    python manage.py fetch_completed_job_logs --limit 50

    # Retry failed fetches
    python manage.py fetch_completed_job_logs --retry-failures

Can be run via cron for automated log collection:
    */15 * * * * cd /path/to/umbrella && python manage.py fetch_completed_job_logs
"""

from django.core.management.base import BaseCommand
from django.db.models import Q
from processes.models import PipeExecution
from umbrella_logger import logger

from workflow.log_fetcher import fetch_job_logs


class Command(BaseCommand):
    help = "Fetch logs for completed SLURM jobs from clusters"

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit",
            type=int,
            default=100,
            help="Maximum number of jobs to process in this run (default: 100)",
        )
        parser.add_argument(
            "--retry-failures",
            action="store_true",
            help="Retry fetching logs that previously failed",
        )
        parser.add_argument(
            "--cluster",
            type=str,
            choices=["czii", "bruno"],
            help="Only fetch logs from specific cluster",
        )

    def handle(self, *args, **options):
        limit = options["limit"]
        retry_failures = options["retry_failures"]
        cluster_filter = options.get("cluster")

        self.stdout.write(self.style.SUCCESS("Starting log fetch for completed jobs..."))

        # Build query
        query = Q(status="completed")

        if retry_failures:
            # Fetch jobs that failed previously OR haven't been tried yet
            query &= Q(logs_fetched_at__isnull=True) | Q(log_fetch_error__isnull=False)
            self.stdout.write("Including previously failed fetches")
        else:
            # Only fetch jobs that haven't been tried yet
            query &= Q(logs_fetched_at__isnull=True)

        # Optionally filter by cluster
        if cluster_filter:
            query &= Q(parameters__cluster_id=cluster_filter)
            self.stdout.write(f"Filtering to cluster: {cluster_filter}")

        # Get executions needing log fetch
        executions = (
            PipeExecution.objects.filter(query)
            .select_related(
                "pipe_in_plan__pipe__software",
                "proc_run",
            )
            .order_by("-completed_at")[:limit]
        )

        total = executions.count()

        if total == 0:
            self.stdout.write(self.style.WARNING("No completed jobs found needing log fetch"))
            return

        self.stdout.write(f"Found {total} jobs to process")

        # Fetch logs for each execution
        success_count = 0
        error_count = 0
        partial_count = 0

        for i, execution in enumerate(executions, 1):
            job_id = execution.job_id or "unknown"
            self.stdout.write(f"[{i}/{total}] Processing job {job_id}...")

            try:
                result = fetch_job_logs(execution)

                if result["success"]:
                    if result["stdout_fetched"] and result["stderr_fetched"]:
                        success_count += 1
                        self.stdout.write(self.style.SUCCESS("  ✓ Fetched both stdout and stderr"))
                    else:
                        partial_count += 1
                        fetched = []
                        if result["stdout_fetched"]:
                            fetched.append("stdout")
                        if result["stderr_fetched"]:
                            fetched.append("stderr")
                        self.stdout.write(self.style.WARNING(f"  ⚠ Partially fetched: {', '.join(fetched)}"))
                else:
                    error_count += 1
                    error = result.get("error", "Unknown error")
                    self.stdout.write(self.style.ERROR(f"  ✗ Failed: {error}"))

            except Exception as e:
                error_count += 1
                logger.exception(f"Unexpected error fetching logs for job {job_id}")
                self.stdout.write(self.style.ERROR(f"  ✗ Unexpected error: {str(e)}"))

        # Print summary
        self.stdout.write(self.style.SUCCESS("\n" + "=" * 60))
        self.stdout.write(self.style.SUCCESS("Log Fetch Summary:"))
        self.stdout.write(f"  Total processed: {total}")
        self.stdout.write(self.style.SUCCESS(f"  Successfully fetched: {success_count}"))
        if partial_count > 0:
            self.stdout.write(self.style.WARNING(f"  Partially fetched: {partial_count}"))
        if error_count > 0:
            self.stdout.write(self.style.ERROR(f"  Errors: {error_count}"))
        self.stdout.write(self.style.SUCCESS("=" * 60))
