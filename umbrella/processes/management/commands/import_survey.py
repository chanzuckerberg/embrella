"""
Register a filesystem survey whose Parquet output already exists on the cluster.

For standing up an environment against surveys that have already been run: the
scan is the expensive part and its Parquet output is still on the cluster, so
only the database rows need regenerating. Creates the FilesystemSurvey row and
re-runs the ingest that derives DirectorySummary and the storage tree from it.

Nothing is written to the cluster -- the Parquet file is read over SFTP.
"""

import os

from django.core.management.base import BaseCommand, CommandError
from stores.models import Cluster

from processes.models import DirectorySummary, FilesystemSurvey, StorageRunSummary

DEFAULT_BASE_PATH = "/hpc/projects/group.czii/krios1.processing/"


class Command(BaseCommand):
    help = "Register a survey from an existing Parquet file on the cluster and ingest it."

    def add_arguments(self, parser):
        parser.add_argument("--cluster", required=True, help="Cluster id, e.g. czii or bruno")
        parser.add_argument(
            "--parquet",
            required=True,
            help="Absolute path to the survey's Parquet file on that cluster",
        )
        parser.add_argument(
            "--base-path",
            default=DEFAULT_BASE_PATH,
            help=f"Root the survey covered; directory depth is measured from it (default: {DEFAULT_BASE_PATH})",
        )
        parser.add_argument(
            "--completed-at",
            help=(
                "The original survey's completion time, ISO 8601. Worth setting: the ingest "
                "fills in `status` but not `completed_at`, and current_survey() orders on it, "
                "so a null loses to any other completed survey on the same cluster."
            ),
        )
        parser.add_argument(
            "--queue",
            action="store_true",
            help=(
                "Hand the ingest to the django-q worker instead of running it here. "
                "Use for a large survey: it survives an ssh disconnect, and progress is in the worker log."
            ),
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Check the cluster and report what would be created, without writing anything",
        )

    def handle(self, *args, **options):
        cluster = options["cluster"]
        parquet = options["parquet"]

        if not Cluster.objects.filter(cluster_id=cluster).exists():
            known = ", ".join(sorted(Cluster.objects.values_list("cluster_id", flat=True))) or "none configured"
            raise CommandError(f"Unknown cluster {cluster!r}. Known clusters: {known}.")

        if not parquet.startswith("/"):
            raise CommandError(f"--parquet must be an absolute path on the cluster, got {parquet!r}")

        size = self._verify_on_cluster(cluster, parquet)
        self.stdout.write(f"Found {parquet} on {cluster} ({size / 1e9:.2f} GB)")

        existing = FilesystemSurvey.objects.filter(cluster=cluster, results_parquet_path=parquet).first()

        if options["dry_run"]:
            verb = f"reuse survey {existing.pk}" if existing else "create a new survey"
            self.stdout.write(f"Dry run: would {verb} for {cluster} and ingest {parquet}")
            return

        survey = existing
        if survey is None:
            survey = FilesystemSurvey.objects.create(
                cluster=cluster,
                base_path=options["base_path"],
                results_parquet_path=parquet,
                status="processing",
                completed_at=options["completed_at"] or None,
            )
            self.stdout.write(f"Created survey {survey.pk} for {cluster}")
        else:
            self.stdout.write(f"Survey {survey.pk} already points at this Parquet; re-ingesting")
            if options["completed_at"]:
                survey.completed_at = options["completed_at"]
                survey.save(update_fields=["completed_at", "updated_at"])

        if not survey.completed_at:
            self.stdout.write(
                self.style.WARNING(
                    "  completed_at is not set. The explorer picks the newest completed survey per "
                    "cluster by that field, so pass --completed-at if this cluster has others.",
                ),
            )

        self._ingest(survey, queue=options["queue"])

    def _verify_on_cluster(self, cluster, parquet):
        """
        Fail before touching the database if the Parquet is not readable.

        Otherwise a typo leaves a survey row behind that no ingest can complete.
        """
        from common import clusterio

        auth = {"username": os.getenv("SLURM_USER"), "key_filename": os.getenv("SLURM_KEYFILE")}
        try:
            ssh = clusterio.get_cluster_ssh_connection(cluster_id=cluster, auth=auth)
            sftp = ssh.open_sftp()
            try:
                return sftp.stat(parquet).st_size
            finally:
                sftp.close()
        except FileNotFoundError as exc:
            raise CommandError(f"{parquet} does not exist on {cluster}") from exc
        except Exception as exc:
            raise CommandError(
                f"Could not read {parquet} from {cluster}: {exc}. "
                "Check SLURM_USER and SLURM_KEYFILE, and that SSH_DISABLED is not set.",
            ) from exc

    def _ingest(self, survey, *, queue):
        if queue:
            from django_q.tasks import async_task

            # survey.cluster explicitly: the task's cluster_id argument defaults
            # to "czii", which would fetch another cluster's Parquet.
            task_id = async_task(
                "processes.tasks.survey_tasks.process_survey_results",
                survey.pk,
                survey.cluster,
            )
            self.stdout.write(f"Queued ingest for survey {survey.pk} on the worker (task {task_id}).")
            self.stdout.write("Follow it with: podman compose ... logs -f worker")
            return

        from processes.tasks.survey_tasks import process_survey_results

        self.stdout.write(f"Ingesting survey {survey.pk}. Large surveys take a while; --queue avoids holding a shell.")
        result = process_survey_results(survey.pk, survey.cluster)

        if result.get("status") == "error":
            raise CommandError(f"Ingest failed: {result.get('error')}")

        survey.refresh_from_db()
        self.stdout.write(
            self.style.SUCCESS(
                f"Survey {survey.pk} ({survey.cluster}) {survey.status}: "
                f"{DirectorySummary.objects.filter(survey=survey).count():,} directories, "
                f"{StorageRunSummary.objects.filter(survey=survey).count():,} storage-tree leaves",
            ),
        )
