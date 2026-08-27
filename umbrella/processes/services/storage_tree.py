"""
Build the storage tree from a filesystem survey, producing StorageRunSummary grouping by session, software, and run.
"""

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from posixpath import basename

from django.db import transaction
from django.db.models import Q

from processes.models import (
    DirectorySummary,
    ProcRun,
    ProcSoftware,
    StorageRunSummary,
    format_bytes,
)

logger = logging.getLogger(__name__)


def script_dir_segments():
    """
    Directory names that hold uploaded SLURM scripts rather than a session.

    Derived from the `script_dir` templates: their last path segment is token-free
    ("scripts"), so no scope or software substitution is needed to know the name.
    """
    from stores.models import PathType

    segments = {
        basename(overlay.rstrip("/"))
        for overlay in PathType.objects.filter(data_kind__data_type="script_dir").values_list("overlay_path", flat=True)
    }
    segments.discard("")

    if not segments:
        logger.warning(
            "No script_dir PathType is configured, so script upload directories cannot be "
            "distinguished from sessions. Expect a spurious 'scripts' session in the tree.",
        )
    return segments


@dataclass
class LeafAccumulator:
    """Running rollup for one (software, session, run) group."""

    directory_count: int = 0
    file_count: int = 0
    total_size_bytes: int = 0
    newest_file_mtime: object = None
    oldest_file_mtime: object = None
    path_prefix: str = ""
    #: bytes per owner, so the winner is the owner of the most data
    owner_bytes: dict = field(default_factory=lambda: defaultdict(int))

    def add(self, path_prefix, file_count, size, newest, oldest, owner):
        self.directory_count += 1
        self.file_count += file_count or 0
        self.total_size_bytes += size or 0

        if newest and (self.newest_file_mtime is None or newest > self.newest_file_mtime):
            self.newest_file_mtime = newest
        if oldest and (self.oldest_file_mtime is None or oldest < self.oldest_file_mtime):
            self.oldest_file_mtime = oldest
        if owner:
            self.owner_bytes[owner] += size or 0

        # Shortest path wins: that is the group's own directory, and every other
        # row in the group is nested below it.
        if not self.path_prefix or len(path_prefix) < len(self.path_prefix):
            self.path_prefix = path_prefix

    @property
    def owner_username(self):
        if not self.owner_bytes:
            return ""
        return max(self.owner_bytes.items(), key=lambda item: (item[1], item[0]))[0]


@dataclass
class BuildReport:
    """What a build did, for the management command and for tests to assert on."""

    survey_id: int = 0
    leaves: int = 0
    created: int = 0
    updated: int = 0
    deleted: int = 0
    rows_scanned: int = 0
    registered_sessions: int = 0
    unregistered_sessions: int = 0
    runs_linked: int = 0
    runs_unlinked: int = 0
    total_size_bytes: int = 0
    directory_count: int = 0
    size_by_software: dict = field(default_factory=dict)
    unregistered_by_size: list = field(default_factory=list)
    dry_run: bool = False

    def as_lines(self):
        """Human-readable summary, newest-relevant facts first."""
        lines = [
            f"Survey {self.survey_id}{' (dry run)' if self.dry_run else ''}",
            f"  scanned {self.rows_scanned:,} directory rows -> {self.leaves:,} leaves",
            f"  created {self.created:,}  updated {self.updated:,}  deleted {self.deleted:,}",
            f"  in tree: {self.directory_count:,} dirs, {format_bytes(self.total_size_bytes)}",
            f"  sessions: {self.registered_sessions} registered, {self.unregistered_sessions} unregistered",
            f"  runs: {self.runs_linked:,} linked to a ProcRun, {self.runs_unlinked:,} on-disk only",
        ]
        if self.size_by_software:
            lines.append("  by software:")
            for software, size in sorted(self.size_by_software.items(), key=lambda kv: -kv[1]):
                lines.append(f"    {software:<16} {format_bytes(size)}")
        if self.unregistered_by_size:
            lines.append("  largest unregistered sessions:")
            for name, size in self.unregistered_by_size:
                lines.append(f"    {name:<36} {format_bytes(size)}")
        return lines


def software_allowlist():
    """
    On-disk directory names that count as Embrella processing software.
    """
    return {
        dirname or name
        for name, dirname in ProcSoftware.objects.values_list("name", "storage_dirname")
        if (dirname or name)
    }


def software_ids_by_dirname():
    """
    Directory name -> ProcSoftware id, for linking a leaf to its software.
    """
    mapping = {}
    for pk, name, dirname in ProcSoftware.objects.order_by("pk").values_list("pk", "name", "storage_dirname"):
        key = dirname or name
        if not key:
            continue
        incumbent = mapping.get(key)
        if incumbent is None or (name == key and incumbent[1] != key):
            mapping[key] = (pk, name)
    return {key: pk for key, (pk, _name) in mapping.items()}


def _prefix_filter(base_path, allowed_software):
    """
    OR of path__startswith, one per allowed software directory.
    """
    condition = Q(pk__in=[])  # matches nothing, so an empty allowlist yields no rows
    for software in sorted(allowed_software):
        condition |= Q(path__startswith=f"{base_path}/{software}/")
    return condition


def _build_run_index():
    """
    (msi_session_id, run_name) -> [(proc_run_id, plan_label)].
    """
    index = defaultdict(list)
    rows = ProcRun.objects.values_list(
        "msi_session_id",
        "name",
        "id",
        "proc_plan__display_name",
        "proc_plan__name",
    ).distinct()
    for session_id, run_name, run_id, plan_display, plan_name in rows:
        label = plan_display or plan_name or ""
        index[(session_id, run_name)].append((run_id, label))
    return index


def _resolve_proc_run(run_index, msi_session_id, run_name, software):
    """
    Pick the ProcRun for a path, or None when Embrella has no record of it.
    """
    if msi_session_id is None or not run_name:
        return None

    candidates = run_index.get((msi_session_id, run_name), [])
    if not candidates:
        return None
    if len(candidates) == 1:
        return candidates[0][0]

    for run_id, label in candidates:
        if label == software:
            return run_id
    return None


def _split_segments(path, base_path):
    """
    Path segments below base_path, or None if the path is not under it.
    """
    if not path.startswith(base_path):
        return None
    return [segment for segment in path[len(base_path) :].split("/") if segment]


@transaction.atomic
def build_storage_tree(survey, *, dry_run=False):
    """
    Rebuild the StorageRunSummary leaves for one survey.

    Idempotent: derived entirely from DirectorySummary, so it can be re-run
    after a fix. Leaves that no longer appear on disk are deleted.
    """
    base_path = survey.base_path.rstrip("/")
    allowed = software_allowlist()
    script_dirs = script_dir_segments()
    report = BuildReport(survey_id=survey.pk, dry_run=dry_run)

    if not allowed:
        logger.warning("No ProcSoftware rows, so nothing can be attributed for survey %s", survey.pk)
        return report

    leaves = defaultdict(LeafAccumulator)

    rows = (
        DirectorySummary.objects.filter(survey=survey, depth__gte=2)
        .filter(_prefix_filter(base_path, allowed))
        .values_list(
            "path",
            "file_count",
            "total_size_bytes",
            "newest_file_mtime",
            "oldest_file_mtime",
            "owner_username",
        )
        .iterator(chunk_size=10_000)
    )

    for path, file_count, size, newest, oldest, owner in rows:
        report.rows_scanned += 1

        segments = _split_segments(path, base_path)
        if segments is None or len(segments) < 2:
            continue

        software, session_name = segments[0], segments[1]
        if software not in allowed or session_name in script_dirs:
            continue

        # Depth-3 is the run. Guarded because a depth-2 row has no run segment;
        # the SQL equivalent of this bug silently returned the whole path.
        run_name = segments[2] if len(segments) >= 3 else ""
        prefix = "/".join([base_path, software, session_name] + ([run_name] if run_name else []))

        leaves[(software, session_name, run_name)].add(prefix, file_count, size, newest, oldest, owner)

    report.leaves = len(leaves)
    if not leaves:
        logger.info("Survey %s produced no storage tree leaves", survey.pk)
        if not dry_run:
            report.deleted = StorageRunSummary.objects.filter(survey=survey).delete()[0]
        return report

    # Resolve links against small in-memory indexes
    from tem.models import MsiSession

    sessions = dict(MsiSession.objects.values_list("name", "id"))
    software_ids = software_ids_by_dirname()
    run_index = _build_run_index()

    unregistered_sizes = defaultdict(int)
    registered_names = set()
    unregistered_names = set()
    summaries = []

    for (software, session_name, run_name), leaf in leaves.items():
        msi_session_id = sessions.get(session_name)
        proc_run_id = _resolve_proc_run(run_index, msi_session_id, run_name, software)

        if msi_session_id is None:
            unregistered_names.add(session_name)
            unregistered_sizes[session_name] += leaf.total_size_bytes
        else:
            registered_names.add(session_name)

        if run_name:
            if proc_run_id is not None:
                report.runs_linked += 1
            else:
                report.runs_unlinked += 1

        report.total_size_bytes += leaf.total_size_bytes
        report.directory_count += leaf.directory_count
        report.size_by_software[software] = report.size_by_software.get(software, 0) + leaf.total_size_bytes

        summaries.append(
            StorageRunSummary(
                survey=survey,
                cluster=survey.cluster,
                software=software,
                session_name=session_name,
                run_name=run_name,
                path_prefix=leaf.path_prefix,
                msi_session_id=msi_session_id,
                proc_run_id=proc_run_id,
                proc_software_id=software_ids.get(software),
                directory_count=leaf.directory_count,
                file_count=leaf.file_count,
                total_size_bytes=leaf.total_size_bytes,
                newest_file_mtime=leaf.newest_file_mtime,
                oldest_file_mtime=leaf.oldest_file_mtime,
                owner_username=leaf.owner_username or "",
            ),
        )

    report.registered_sessions = len(registered_names)
    report.unregistered_sessions = len(unregistered_names)
    report.unregistered_by_size = sorted(unregistered_sizes.items(), key=lambda kv: -kv[1])[:10]

    existing_keys = set(
        StorageRunSummary.objects.filter(survey=survey).values_list("software", "session_name", "run_name"),
    )
    incoming_keys = set(leaves.keys())
    report.created = len(incoming_keys - existing_keys)
    report.updated = len(incoming_keys & existing_keys)
    report.deleted = len(existing_keys - incoming_keys)

    # Counted before returning so a dry run reports what it *would* change.
    if dry_run:
        return report

    StorageRunSummary.objects.filter(survey=survey).delete()
    StorageRunSummary.objects.bulk_create(summaries, batch_size=1000)

    logger.info(
        "Built storage tree for survey %s: %s leaves, %s",
        survey.pk,
        report.leaves,
        format_bytes(report.total_size_bytes),
    )
    return report


def tree_is_stale(survey):
    """
    True when the survey has been touched since its tree was built.
    """
    oldest_build = (
        StorageRunSummary.objects.filter(survey=survey).order_by("built_at").values_list("built_at", flat=True).first()
    )
    if oldest_build is None:
        return DirectorySummary.objects.filter(survey=survey).exists()
    return survey.updated_at is not None and survey.updated_at > oldest_build
