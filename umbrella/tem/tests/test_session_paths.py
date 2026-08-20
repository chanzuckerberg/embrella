"""
Characterization tests for session path resolution.

These pin down what `MsiSession`/`AtlasSession` path resolution does *today*, so the
scope-aware rework changes behaviour visibly rather than incidentally.

Templates mirror the real seeds in scripts/001_init.py so the substitution behaviour
under test is the production one.
"""

import pytest
from stores.models import Path, PathType, StaticPath

from tem.models import (
    AtlasSession,
    Camera,
    ImagingWorkflow,
    Microscope,
    MsiSession,
    ScreenSessionGroup,
    SessionPlan,
    Software,
)

FRAMES_STATIC = "/{workflow}/{msi_session}/{run}/frames"
FRAMES_OVERLAY = "/hpc/instruments/czii.{scope}/OffloadData/{msi_session}/{run}_{sequence}_{tilt}_*.eer"
MDOC_STATIC = "/{workflow}/{msi_session}/{run}/mdoc"
MDOC_OVERLAY = "/hpc/instruments/czii.{scope}/OffloadData/{msi_session}/{run}.mdoc"
ATLAS_OVERLAY = (
    "/hpc/instruments/czii.{scope}/OffloadData/{workflow}/{session_group}/{atlas_session}/Atlas/Atlas_{timestamp}.mrc"
)


def make_path_type(data_type, static_path, overlay_path):
    return PathType.objects.create(
        static_path=StaticPath.objects.create(data_type=data_type, static_path=static_path),
        overlay_path=overlay_path,
    )


@pytest.fixture
def microscope(db):
    return Microscope.objects.create(name="krios1", cs=2.7)


@pytest.fixture
def camera(db):
    return Camera.objects.create(
        name="Falcon4i",
        root_dir="/hpc/instruments/czii.krios1/OffloadData/",
        frame_format="eer",
        initial_frame_base_dir="/OffloadData/",
    )


@pytest.fixture
def software(db):
    """Software with real path FKs -- the fixtures elsewhere leave all five NULL."""
    return Software.objects.create(
        name="tomo5",
        frames=make_path_type("frames", FRAMES_STATIC, FRAMES_OVERLAY),
        mdocs=make_path_type("mdoc", MDOC_STATIC, MDOC_OVERLAY),
    )


@pytest.fixture
def bare_software(db):
    """Software with no path FKs at all, as tem/processes fixtures create it."""
    return Software.objects.create(name="BareSoftware")


@pytest.fixture
def imaging_workflow(db):
    return ImagingWorkflow.objects.create(imaging_mode="tem", workflow="tomo")


@pytest.fixture
def session_plan(db, microscope, camera, software, imaging_workflow):
    return SessionPlan.objects.create(
        scope=microscope,
        camera=camera,
        imaging_workflow=imaging_workflow,
        software=software,
    )


@pytest.fixture
def msi_session(db, session_plan):
    return MsiSession.objects.create(name="24nov10", session_plan=session_plan)


@pytest.mark.django_db
class TestGetSessionGlob:
    def test_substitutes_session_scoped_tokens(self, msi_session):
        glob = msi_session.get_session_frames_glob()
        assert glob.startswith("/hpc/instruments/czii.krios1/OffloadData/24nov10/")

    def test_leaves_file_scoped_tokens_unsubstituted(self, msi_session):
        """The replacement map supplies only workflow/scope/msi_session, so per-file
        tokens survive verbatim -- which is why the stored string is neither a valid
        path nor a valid glob."""
        glob = msi_session.get_session_frames_glob()
        assert "{run}" in glob
        assert "{sequence}" in glob
        assert "{tilt}" in glob

    def test_scope_token_is_not_lowercased(self, db, microscope, camera, software, imaging_workflow):
        """Lane A uses raw `scope.name` while resolve_review_path lowercases.
        Pinned so the normalisation is a visible change."""
        microscope.name = "Krios1"
        microscope.save()
        plan = SessionPlan.objects.create(
            scope=microscope, camera=camera, imaging_workflow=imaging_workflow, software=software
        )
        session = MsiSession.objects.create(name="24nov11", session_plan=plan)
        assert "czii.Krios1/" in session.get_session_frames_glob()

    def test_camera_fields_are_not_available_as_tokens(self, db, msi_session, software):
        """Camera.frame_format/root_dir exist but no replacement map supplies them."""
        software.frames.overlay_path = "/data/{camera}/{frame_format}/{msi_session}/"
        software.frames.save()
        assert msi_session.get_session_frames_glob() == "/data/{camera}/{frame_format}/24nov10/"

    def test_returns_dot_when_software_role_is_null(self, db, bare_software, microscope, camera, imaging_workflow):
        plan = SessionPlan.objects.create(
            scope=microscope, camera=camera, imaging_workflow=imaging_workflow, software=bare_software
        )
        session = MsiSession.objects.create(name="24nov12", session_plan=plan)
        assert session.get_session_frames_glob() == "."


@pytest.mark.django_db
class TestGetSessionPath:
    def test_creates_path_with_both_halves_filled(self, msi_session):
        p = msi_session.get_session_path("frames")
        assert p.overlay_path.startswith("/hpc/instruments/czii.krios1/OffloadData/24nov10/")
        assert p.static_path == "/tomo/24nov10/{run}/frames"

    def test_is_idempotent(self, msi_session):
        """Second call reuses the row rather than duplicating it."""
        first = msi_session.get_session_path("frames")
        second = msi_session.get_session_path("frames")
        assert first.pk == second.pk
        assert Path.objects.count() == 1

    def test_distinct_roles_produce_distinct_rows_today(self, msi_session):
        """Pre-split, frames and mdocs differ because the filename half is baked in.
        After the Phase 2b split both resolve to the same directory and collapse to
        one row -- assert the current shape so that change is deliberate."""
        frames = msi_session.get_session_path("frames")
        mdocs = msi_session.get_session_path("mdocs")
        assert frames.pk != mdocs.pk
        assert Path.objects.count() == 2

    def test_stored_overlay_retains_file_scoped_tokens(self, msi_session):
        """Nothing globs this string, which is why the unsubstituted tokens survive
        all the way into the database."""
        p = msi_session.get_session_path("frames")
        assert "{run}" in p.overlay_path


@pytest.mark.django_db
class TestAtlasSessionPaths:
    @pytest.fixture
    def atlas_session(self, db, session_plan, software):
        software.atlas = make_path_type("atlas", "/{workflow}/{session_group}/atlas", ATLAS_OVERLAY)
        software.save()
        group = ScreenSessionGroup.objects.create(name="grp1", session_plan=session_plan)
        return AtlasSession.objects.create(name="scrn1", group=group)

    def test_substitutes_group_and_atlas_session_tokens(self, atlas_session):
        glob = atlas_session.get_session_atlas_glob()
        assert "/tomo/grp1/scrn1/Atlas/" in glob

    def test_leaves_timestamp_unsubstituted(self, atlas_session):
        assert "{timestamp}" in atlas_session.get_session_atlas_glob()

    def test_returns_dot_when_software_role_is_null(self, db, session_plan):
        session_plan.software.atlas = None
        session_plan.software.save()
        group = ScreenSessionGroup.objects.create(name="grp2", session_plan=session_plan)
        atlas = AtlasSession.objects.create(name="scrn2", group=group)
        assert atlas.get_session_atlas_glob() == "."
