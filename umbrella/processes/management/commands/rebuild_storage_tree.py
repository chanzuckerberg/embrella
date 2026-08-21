"""
Rebuild the StorageRunSummary leaves for one or all surveys.

Safe to re-run: the tree is derived entirely from DirectorySummary.
"""

from django.core.management.base import BaseCommand, CommandError

from processes.models import FilesystemSurvey, current_survey
from processes.services.storage_tree import build_storage_tree, tree_is_stale


class Command(BaseCommand):
    help = "Rebuild the storage tree (StorageRunSummary) from DirectorySummary rows."

    def add_arguments(self, parser):
        parser.add_argument("--survey", type=int, help="Survey id to rebuild")
        parser.add_argument(
            "--current",
            action="store_true",
            help="Rebuild the newest completed survey on each cluster -- the trees the UI reads",
        )
        parser.add_argument(
            "--all",
            action="store_true",
            help="Rebuild every survey, including superseded ones. For backfill or after a builder fix.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report what would be written without touching the database",
        )
        parser.add_argument(
            "--check",
            action="store_true",
            help="Exit non-zero if any surveyed tree is stale. Writes nothing.",
        )

    def handle(self, *args, **options):
        if options["check"]:
            return self._check()

        if not any((options["survey"], options["current"], options["all"])):
            raise CommandError("Pass --current, --survey ID, --all, or --check")

        for survey in self._surveys(options):
            report = build_storage_tree(survey, dry_run=options["dry_run"])
            if report.rows_scanned == 0 and report.leaves == 0:
                self.stdout.write(f"Survey {survey.pk} ({survey.cluster}): no directory rows in range, skipped")
                continue
            for line in report.as_lines():
                self.stdout.write(line)

    def _surveys(self, options):
        """Which surveys to rebuild, most specific option first."""
        if options["survey"]:
            survey = FilesystemSurvey.objects.filter(pk=options["survey"]).first()
            if survey is None:
                raise CommandError(f"No survey with id {options['survey']}")
            return [survey]

        if options["current"]:
            # One per cluster, deduplicated: two clusters can in principle share
            # a newest survey id only if the data is odd, but dict-by-pk keeps
            # this honest either way.
            clusters = FilesystemSurvey.objects.values_list("cluster", flat=True).distinct()
            newest = {}
            for cluster in clusters:
                survey = current_survey(cluster)
                if survey is None:
                    self.stdout.write(f"{cluster}: no completed survey, nothing to build")
                else:
                    newest[survey.pk] = survey
            return [newest[pk] for pk in sorted(newest)]

        return list(FilesystemSurvey.objects.order_by("id"))

    def _check(self):
        """Report stale trees without writing. Non-zero exit so CI or cron can gate on it."""
        stale = [survey for survey in FilesystemSurvey.objects.order_by("id") if tree_is_stale(survey)]
        if not stale:
            self.stdout.write(self.style.SUCCESS("All storage trees are up to date"))
            return

        for survey in stale:
            self.stdout.write(
                self.style.WARNING(f"Survey {survey.pk} ({survey.cluster}) has a stale or missing storage tree"),
            )
        raise CommandError(f"{len(stale)} survey(s) need rebuild_storage_tree")
