"""
Tests for the storage tree builder
"""

from datetime import datetime, timezone

import pytest
from tem.models import MsiSession

from processes.models import (
    DirectorySummary,
    FilesystemSurvey,
    ProcPlan,
    ProcRun,
    ProcSoftware,
    StorageRunSummary,
)
from processes.services.storage_tree import build_storage_tree, tree_is_stale

BASE = "/hpc/projects/group.czii/krios1.processing"


def dt(day, hour=12):
    return datetime(2026, 5, day, hour, tzinfo=timezone.utc)


@pytest.fixture
def survey(db):
    return FilesystemSurvey.objects.create(
        cluster="czii",
        base_path=f"{BASE}/",
        status="completed",
    )


@pytest.fixture
def software(db):
    """
    The allowlist, and only the allowlist.
    """
    ProcSoftware.objects.all().delete()
    for name in ["aretomo3", "denoise", "copick"]:
        ProcSoftware.objects.create(
            name=name,
            version="test",
            storage_dirname=name,
            script_directory=f"{BASE}/{name}/scripts",
        )
    ProcSoftware.objects.create(name="pytom", version="test", storage_dirname="pytom")
    return ProcSoftware.objects.all()


@pytest.fixture
def make_dir(survey):
    def _make(path, *, size=1000, files=10, depth=None, newest=None, oldest=None, owner="alice"):
        relative = path[len(survey.base_path.rstrip("/")) :].strip("/")
        return DirectorySummary.objects.create(
            survey=survey,
            cluster="czii",
            path=path,
            file_count=files,
            total_size_bytes=size,
            owner_username=owner,
            depth=len(relative.split("/")) if depth is None else depth,
            newest_file_mtime=newest or dt(1),
            oldest_file_mtime=oldest or dt(1),
        )

    return _make


def leaves_by_key(survey):
    return {
        (leaf.software, leaf.session_name, leaf.run_name): leaf
        for leaf in StorageRunSummary.objects.filter(survey=survey)
    }


@pytest.mark.django_db
class TestSegmentParsing:
    def test_groups_by_software_session_and_run(self, survey, software, make_dir):
        make_dir(f"{BASE}/aretomo3/26mar02a/run001", size=100)
        make_dir(f"{BASE}/aretomo3/26mar02a/run001/Position_1_Imod", size=900)
        make_dir(f"{BASE}/aretomo3/26mar02a/run002", size=500)

        build_storage_tree(survey)
        leaves = leaves_by_key(survey)

        assert set(leaves) == {("aretomo3", "26mar02a", "run001"), ("aretomo3", "26mar02a", "run002")}
        # Everything below the run rolls up into it -- that is the whole point,
        # since per-position directories are ~81% of a real survey.
        assert leaves[("aretomo3", "26mar02a", "run001")].total_size_bytes == 1000
        assert leaves[("aretomo3", "26mar02a", "run001")].directory_count == 2

    def test_depth_two_row_becomes_a_run_less_leaf(self, survey, software, make_dir):
        """
        A session directory holding files but no run subdirectory.
        """
        make_dir(f"{BASE}/aretomo3/26mar02a", size=4200)

        build_storage_tree(survey)

        leaf = StorageRunSummary.objects.get(survey=survey)
        assert leaf.run_name == ""
        assert leaf.total_size_bytes == 4200
        assert leaf.path_prefix == f"{BASE}/aretomo3/26mar02a"

    def test_pipe_segment_is_recorded_as_the_run(self, survey, software, make_dir):
        """
        Documents a known v1 limitation, so a future fix has a failing test.

        pytom/slabpick/membraneseg use {software}/{session}/{pipe}/{run}/, so the
        depth-3 segment is the pipe. Correct behaviour would resolve `run001`;
        v1 records `voxelspacing10.000a`.
        """
        make_dir(f"{BASE}/pytom/26mar02a/voxelspacing10.000a/run001", size=700)

        build_storage_tree(survey)

        leaf = StorageRunSummary.objects.get(survey=survey)
        assert leaf.run_name == "voxelspacing10.000a"

    def test_scripts_directory_is_not_a_session(self, survey, software, make_dir):
        """
        The script upload directory sits in the session position.

        Recognised from ProcSoftware.script_directory rather than a hardcoded
        name, so a deployment that uploads somewhere else works without a code
        change.
        """
        make_dir(f"{BASE}/aretomo3/scripts", size=10)
        make_dir(f"{BASE}/aretomo3/scripts/pyConvert/lib/python3.10/site-packages", size=90)
        make_dir(f"{BASE}/aretomo3/26mar02a/run001", size=500)

        build_storage_tree(survey)

        leaves = leaves_by_key(survey)
        assert set(leaves) == {("aretomo3", "26mar02a", "run001")}

    def test_scripts_excluded_for_software_with_no_script_directory(self, survey, software, make_dir):
        """
        pytom has a NULL script_directory but a real pytom/scripts holding 15.7 GB.

        Matching exact script_directory prefixes would miss it, so the segment
        name is taken from whichever rows do set the field and applied to all.
        """
        make_dir(f"{BASE}/pytom/scripts", size=15_700)
        make_dir(f"{BASE}/pytom/26mar02a/run001", size=500)

        build_storage_tree(survey)

        assert set(leaves_by_key(survey)) == {("pytom", "26mar02a", "run001")}

    def test_scripts_directory_name_comes_from_the_database(self, survey, software, make_dir):
        """A deployment uploading to `bin` instead of `scripts` needs no code change."""
        ProcSoftware.objects.filter(name="aretomo3").update(script_directory=f"{BASE}/aretomo3/bin")
        make_dir(f"{BASE}/aretomo3/bin/whatever", size=90)
        make_dir(f"{BASE}/aretomo3/26mar02a/run001", size=500)

        build_storage_tree(survey)

        assert set(leaves_by_key(survey)) == {("aretomo3", "26mar02a", "run001")}

    def test_non_allowlisted_software_is_excluded(self, survey, software, make_dir):
        """relion and warptools are real on bruno but are not Embrella-run."""
        make_dir(f"{BASE}/relion/kagglePaper/Class3D/job005", size=10_000)
        make_dir(f"{BASE}/software/foo", size=20)
        make_dir(f"{BASE}/aretomo3/26mar02a/run001", size=500)

        report = build_storage_tree(survey)

        assert set(leaves_by_key(survey)) == {("aretomo3", "26mar02a", "run001")}
        assert report.total_size_bytes == 500

    def test_bare_software_directory_is_skipped(self, survey, software, make_dir):
        """depth-1 has no session segment at all."""
        make_dir(f"{BASE}/aretomo3", size=5, depth=1)

        build_storage_tree(survey)

        assert StorageRunSummary.objects.count() == 0


@pytest.mark.django_db
class TestRollups:
    def test_rollup_matches_the_underlying_rows(self, survey, software, make_dir):
        make_dir(f"{BASE}/aretomo3/26mar02a/run001", size=100, files=1, newest=dt(1), oldest=dt(1))
        make_dir(f"{BASE}/aretomo3/26mar02a/run001/vol001", size=250, files=4, newest=dt(9), oldest=dt(3))
        make_dir(f"{BASE}/denoise/26mar02a/run001", size=70, files=2, newest=dt(5), oldest=dt(2))

        build_storage_tree(survey)
        leaves = leaves_by_key(survey)

        aretomo = leaves[("aretomo3", "26mar02a", "run001")]
        assert aretomo.total_size_bytes == 350
        assert aretomo.file_count == 5
        assert aretomo.directory_count == 2
        assert aretomo.newest_file_mtime == dt(9)
        assert aretomo.oldest_file_mtime == dt(1)

        # The invariant that matters: the tree must account for every allowlisted byte.
        selected = DirectorySummary.objects.filter(survey=survey, depth__gte=2)
        assert sum(leaf.total_size_bytes for leaf in leaves.values()) == sum(row.total_size_bytes for row in selected)

    def test_owner_is_the_owner_of_the_most_bytes(self, survey, software, make_dir):
        make_dir(f"{BASE}/aretomo3/26mar02a/run001", size=10, owner="alice")
        make_dir(f"{BASE}/aretomo3/26mar02a/run001/a", size=10, owner="alice")
        make_dir(f"{BASE}/aretomo3/26mar02a/run001/b", size=5000, owner="bob")

        build_storage_tree(survey)

        # Two directories to alice's one, but bob owns nearly all the data.
        assert StorageRunSummary.objects.get(survey=survey).owner_username == "bob"

    def test_path_prefix_is_the_shallowest_directory_in_the_group(self, survey, software, make_dir):
        make_dir(f"{BASE}/aretomo3/26mar02a/run001/Position_9_Imod", size=1)
        make_dir(f"{BASE}/aretomo3/26mar02a/run001", size=1)

        build_storage_tree(survey)

        assert StorageRunSummary.objects.get(survey=survey).path_prefix == f"{BASE}/aretomo3/26mar02a/run001"


@pytest.mark.django_db
class TestLinkResolution:
    def test_registered_session_links_and_unregistered_does_not(self, survey, software, make_dir, session_plan):
        known = MsiSession.objects.create(name="26mar02a", session_plan=session_plan)
        make_dir(f"{BASE}/aretomo3/26mar02a/run001", size=100)
        make_dir(f"{BASE}/aretomo3/20240308_002_Krios1_RP_Lys6prtns/run001", size=900)

        report = build_storage_tree(survey)
        leaves = leaves_by_key(survey)

        assert leaves[("aretomo3", "26mar02a", "run001")].msi_session_id == known.pk
        assert leaves[("aretomo3", "26mar02a", "run001")].registered is True

        # Unregistered means "not linked", never "not shown" -- on bruno this
        # tree is the single largest reclaim candidate.
        orphan = leaves[("aretomo3", "20240308_002_Krios1_RP_Lys6prtns", "run001")]
        assert orphan.msi_session_id is None
        assert orphan.registered is False
        assert orphan.total_size_bytes == 900

        assert report.registered_sessions == 1
        assert report.unregistered_sessions == 1

    def test_long_session_name_is_not_truncated(self, survey, software, make_dir):
        """MsiSession.name allows 20 chars; real on-disk names exceed it."""
        name = "20240308_002_Krios1_RP_Lys6prtns"
        make_dir(f"{BASE}/aretomo3/{name}/run001")

        build_storage_tree(survey)

        assert StorageRunSummary.objects.get(survey=survey).session_name == name

    def test_duplicate_run_name_is_disambiguated_by_software(self, survey, software, make_dir, session_plan):
        """
        One session with `run001` under two plans
        """
        session = MsiSession.objects.create(name="26mar02a", session_plan=session_plan)
        aretomo_plan = ProcPlan.objects.create(name="czii-live", display_name="aretomo3")
        denoise_plan = ProcPlan.objects.create(name="czii-denoise", display_name="denoise")
        aretomo_run = ProcRun.objects.create(name="run001", msi_session=session, proc_plan=aretomo_plan)
        denoise_run = ProcRun.objects.create(name="run001", msi_session=session, proc_plan=denoise_plan)

        make_dir(f"{BASE}/aretomo3/26mar02a/run001", size=100)
        make_dir(f"{BASE}/denoise/26mar02a/run001", size=200)

        build_storage_tree(survey)
        leaves = leaves_by_key(survey)

        assert leaves[("aretomo3", "26mar02a", "run001")].proc_run_id == aretomo_run.pk
        assert leaves[("denoise", "26mar02a", "run001")].proc_run_id == denoise_run.pk

    def test_on_disk_run_with_no_record_stays_visible(self, survey, software, make_dir, session_plan):
        MsiSession.objects.create(name="26mar02a", session_plan=session_plan)
        make_dir(f"{BASE}/aretomo3/26mar02a/run099", size=300)

        report = build_storage_tree(survey)

        leaf = StorageRunSummary.objects.get(survey=survey)
        assert leaf.proc_run_id is None
        assert leaf.run_name == "run099"
        assert report.runs_unlinked == 1

    def test_proc_software_is_linked_by_directory_name(self, survey, software, make_dir):
        make_dir(f"{BASE}/aretomo3/26mar02a/run001")

        build_storage_tree(survey)

        leaf = StorageRunSummary.objects.get(survey=survey)
        assert leaf.proc_software.name == "aretomo3"


@pytest.mark.django_db
class TestRebuild:
    def test_build_is_idempotent(self, survey, software, make_dir):
        make_dir(f"{BASE}/aretomo3/26mar02a/run001", size=100)

        first = build_storage_tree(survey)
        second = build_storage_tree(survey)

        assert StorageRunSummary.objects.count() == 1
        assert first.created == 1
        assert second.created == 0
        assert second.updated == 1

    def test_leaves_that_vanish_are_deleted(self, survey, software, make_dir):
        keep = make_dir(f"{BASE}/aretomo3/26mar02a/run001", size=100)
        gone = make_dir(f"{BASE}/aretomo3/26mar02a/run002", size=100)
        build_storage_tree(survey)
        assert StorageRunSummary.objects.count() == 2

        gone.delete()
        report = build_storage_tree(survey)

        assert report.deleted == 1
        assert [leaf.run_name for leaf in StorageRunSummary.objects.all()] == ["run001"]
        assert keep.pk  # untouched

    def test_dry_run_writes_nothing_but_still_reports(self, survey, software, make_dir):
        make_dir(f"{BASE}/aretomo3/26mar02a/run001", size=100)

        report = build_storage_tree(survey, dry_run=True)

        assert StorageRunSummary.objects.count() == 0
        assert report.leaves == 1
        assert report.total_size_bytes == 100

    def test_stale_when_survey_changes_after_build(self, survey, software, make_dir):
        make_dir(f"{BASE}/aretomo3/26mar02a/run001")
        build_storage_tree(survey)
        assert tree_is_stale(survey) is False

        survey.save()  # auto_now bumps updated_at, as a reprocess would

        assert tree_is_stale(survey) is True

    def test_stale_when_rows_exist_but_no_tree(self, survey, software, make_dir):
        make_dir(f"{BASE}/aretomo3/26mar02a/run001")

        assert tree_is_stale(survey) is True


@pytest.mark.django_db
class TestDecisions:
    def test_decision_survives_a_new_survey(self, survey, software, make_dir, django_user_model):
        """
        The property that motivated a separate table.

        A status on DirectorySummary would be stranded with new surveys
        """
        from processes.models import StorageDecision

        user = django_user_model.objects.create(username="alice")
        prefix = f"{BASE}/aretomo3/26mar02a/run001"
        StorageDecision.objects.create(cluster="czii", path_prefix=prefix, status="delete", decided_by=user)

        later = FilesystemSurvey.objects.create(cluster="czii", base_path=f"{BASE}/", status="completed")
        DirectorySummary.objects.create(
            survey=later,
            cluster="czii",
            path=prefix,
            depth=3,
            total_size_bytes=100,
        )
        build_storage_tree(later)

        leaf = StorageRunSummary.objects.get(survey=later)
        decision = StorageDecision.objects.get(cluster=leaf.cluster, path_prefix=leaf.path_prefix)
        assert decision.status == "delete"
        assert decision.decided_by == user


@pytest.mark.django_db
class TestCurrentScoping:
    """
    The table holds one tree per survey, so reads must be scoped or they sum
    every survey on every cluster together -- quietly, and with a
    plausible-looking number.
    """

    def _survey(self, cluster, completed_at, **kwargs):
        return FilesystemSurvey.objects.create(
            cluster=cluster,
            base_path=f"{BASE}/",
            status=kwargs.pop("status", "completed"),
            completed_at=completed_at,
        )

    def test_current_picks_the_newest_completed_survey(self, software, session_plan):
        older = self._survey("czii", dt(1))
        newer = self._survey("czii", dt(9))
        for survey, size in ((older, 100), (newer, 500)):
            DirectorySummary.objects.create(
                survey=survey,
                cluster="czii",
                path=f"{BASE}/aretomo3/26mar02a/run001",
                depth=3,
                total_size_bytes=size,
            )
            build_storage_tree(survey)

        current = StorageRunSummary.objects.current("czii")

        assert [leaf.survey_id for leaf in current] == [newer.pk]
        assert current.get().total_size_bytes == 500

    def test_current_isolates_clusters(self, software):
        czii = self._survey("czii", dt(5))
        bruno = self._survey("bruno", dt(5))
        for survey in (czii, bruno):
            DirectorySummary.objects.create(
                survey=survey,
                cluster=survey.cluster,
                path=f"{BASE}/aretomo3/26mar02a/run001",
                depth=3,
                total_size_bytes=200,
            )
            build_storage_tree(survey)

        # Unscoped spans both clusters -- the mistake this guards against.
        assert StorageRunSummary.objects.count() == 2
        assert StorageRunSummary.objects.current("czii").count() == 1
        assert StorageRunSummary.objects.current("bruno").count() == 1

    def test_incomplete_survey_is_never_current(self, software):
        done = self._survey("czii", dt(1))
        DirectorySummary.objects.create(
            survey=done,
            cluster="czii",
            path=f"{BASE}/aretomo3/26mar02a/run001",
            depth=3,
            total_size_bytes=100,
        )
        build_storage_tree(done)

        running = self._survey("czii", dt(9), status="running")
        DirectorySummary.objects.create(
            survey=running,
            cluster="czii",
            path=f"{BASE}/aretomo3/26mar02a/run002",
            depth=3,
            total_size_bytes=999,
        )
        build_storage_tree(running)

        # A survey still being processed must not become the view of the cluster.
        assert [leaf.run_name for leaf in StorageRunSummary.objects.current("czii")] == ["run001"]

    def test_cluster_with_no_completed_survey_is_empty_not_an_error(self, software):
        self._survey("czii", None, status="running")

        assert StorageRunSummary.objects.current("czii").count() == 0
        assert StorageRunSummary.objects.current("nonexistent").count() == 0

    def test_rebuilding_a_superseded_survey_does_not_change_what_is_current(self, software):
        """
        Guards the ingest hook's assumption.

        process_survey_results builds only the survey it just finished, which is
        normally the newest and therefore becomes the cluster's view. Reprocessing
        an older survey must refresh that survey's own tree without hijacking the
        current one -- the hook logs a warning for exactly this case.
        """
        older = self._survey("czii", dt(1))
        newer = self._survey("czii", dt(9))
        for survey, size in ((older, 100), (newer, 500)):
            DirectorySummary.objects.create(
                survey=survey,
                cluster="czii",
                path=f"{BASE}/aretomo3/26mar02a/run001",
                depth=3,
                total_size_bytes=size,
            )
            build_storage_tree(survey)

        # Reprocess the older one.
        DirectorySummary.objects.filter(survey=older).update(total_size_bytes=7777)
        build_storage_tree(older)

        assert StorageRunSummary.objects.get(survey=older).total_size_bytes == 7777
        assert StorageRunSummary.objects.current("czii").get().total_size_bytes == 500
