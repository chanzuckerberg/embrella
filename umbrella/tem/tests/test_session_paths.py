"""
Tests for session path resolution.
"""

import pytest
from stores.models import DataKind, FilePattern, Path, PathType
from stores.paths import UnresolvedPlaceholderError

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

# frames and mdocs share this directory -- what tells them apart is the file pattern.
SESSION_DIR = "/hpc/instruments/czii.{scope}/OffloadData/{msi_session}/"
ATLAS_DIR = "/hpc/instruments/czii.{scope}/OffloadData/{workflow}/{session_group}/{atlas_session}/Atlas/"

FRAMES_PATTERN = {
    "label": "{run}_{sequence}_{tilt}_*.eer",
    "list_glob": "*.eer",
    "regex": r"^(?P<run>.+)_(?P<sequence>\d+)_(?P<tilt>-?\d+(?:\.\d+)?)_.*\.eer$",
}
MDOC_PATTERN = {"label": "{run}.mdoc", "list_glob": "*.mdoc", "regex": r"^(?P<run>.+)\.mdoc$"}
ATLAS_PATTERN = {
    "label": "Atlas_{timestamp}.mrc",
    "list_glob": "Atlas_*.mrc",
    "regex": r"^Atlas_(?P<timestamp>[\w-]+)\.mrc$",
}


def make_path_type(data_type, overlay_path, pattern=None):
    data_kind = DataKind.objects.create(data_type=data_type)
    return PathType.objects.create(
        data_kind=data_kind,
        overlay_path=overlay_path,
        file_pattern=FilePattern.objects.create(data_kind=data_kind, **pattern) if pattern else None,
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
        frames=make_path_type("frames", SESSION_DIR, FRAMES_PATTERN),
        mdocs=make_path_type("mdoc", SESSION_DIR, MDOC_PATTERN),
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
class TestGetSessionDir:
    def test_substitutes_session_scoped_tokens(self, msi_session):
        assert msi_session.get_session_dir("frames") == "/hpc/instruments/czii.krios1/OffloadData/24nov10/"

    def test_nothing_is_left_unsubstituted(self, msi_session):
        assert "{" not in msi_session.get_session_dir("frames")

    def test_scope_name_is_used_verbatim(self, db, microscope, camera, software, imaging_workflow):
        """Microscope.name is the path segment itself, so no case is forced on it. Our
        scopes are lowercase by convention, but an install whose directories are spelled
        "Krios1" must work."""
        microscope.name = "Krios1"
        microscope.save()
        plan = SessionPlan.objects.create(
            scope=microscope, camera=camera, imaging_workflow=imaging_workflow, software=software
        )
        session = MsiSession.objects.create(name="24nov11", session_plan=plan)
        assert "czii.Krios1/" in session.get_session_dir("frames")

    def test_camera_fields_are_available_as_tokens(self, db, msi_session, software):
        """A camera difference (.eer vs .tiff, a different mount root) resolves by
        substitution, so it needs no per-plan config row. The trailing slash on
        Camera.root_dir is stripped -- templates supply their own separators."""
        software.frames.overlay_path = "{root_dir}/{camera}/{frame_format}/{msi_session}/"
        software.frames.save()
        assert msi_session.get_session_dir("frames") == "/hpc/instruments/czii.krios1/OffloadData/Falcon4i/eer/24nov10/"

    def test_returns_dot_when_software_role_is_null(self, db, bare_software, microscope, camera, imaging_workflow):
        plan = SessionPlan.objects.create(
            scope=microscope, camera=camera, imaging_workflow=imaging_workflow, software=bare_software
        )
        session = MsiSession.objects.create(name="24nov12", session_plan=plan)
        assert session.get_session_dir("frames") == "."


@pytest.mark.django_db
class TestResolvePathRow:
    def test_creates_path_with_overlay_filled(self, msi_session):
        p = msi_session._resolve_path_row("frames")
        assert p.overlay_path == "/hpc/instruments/czii.krios1/OffloadData/24nov10/"

    def test_is_idempotent(self, msi_session):
        """Second call reuses the row rather than duplicating it."""
        first = msi_session._resolve_path_row("frames")
        second = msi_session._resolve_path_row("frames")
        assert first.pk == second.pk
        assert Path.objects.count() == 1

    def test_roles_sharing_a_directory_share_one_row(self, msi_session):
        """Pre-split, frames and mdocs differed only by the filename half baked into the
        string. Both are the same folder, so they now collapse to one Path row -- what
        distinguishes them moved to FilePattern."""
        assert msi_session._resolve_path_row("frames").pk == msi_session._resolve_path_row("mdocs").pk
        assert Path.objects.count() == 1

    def test_stored_overlay_has_no_placeholders(self, msi_session):
        """The acceptance criterion for the split, at the point where it gets persisted."""
        assert "{" not in msi_session._resolve_path_row("frames").overlay_path

    def test_raises_when_a_template_kept_its_filename_half(self, msi_session, software):
        """An unsplit template can only produce a path to nothing, so it fails loudly
        instead of being stored."""
        software.frames.overlay_path = "/hpc/{msi_session}/{run}_{tilt}.eer"
        software.frames.save()
        with pytest.raises(UnresolvedPlaceholderError, match="belong in a FilePattern capture group"):
            msi_session._resolve_path_row("frames")


@pytest.mark.django_db
class TestGetFilePattern:
    def test_resolves_the_directorys_own_pattern(self, msi_session):
        assert msi_session.get_file_pattern("frames").list_glob == "*.eer"

    def test_roles_sharing_a_directory_still_have_distinct_patterns(self, msi_session):
        assert msi_session.get_file_pattern("mdocs").list_glob == "*.mdoc"

    def test_the_pattern_reads_back_what_the_directory_cannot_supply(self, msi_session):
        """Directory fills downward, pattern parses upward: together they cover the tokens
        the single combined template used to carry."""
        groups = msi_session.get_file_pattern("frames").match("Position_96_2_001_-30.0_Fractions.eer")
        assert groups == {"run": "Position_96_2", "sequence": "001", "tilt": "-30.0"}

    def test_is_none_when_the_role_is_unset(self, db, bare_software, session_plan):
        session_plan.software = bare_software
        session_plan.save()
        session = MsiSession.objects.create(name="24nov13", session_plan=session_plan)
        assert session.get_file_pattern("frames") is None


@pytest.mark.django_db
class TestAtlasSessionPaths:
    @pytest.fixture
    def atlas_session(self, db, session_plan, software):
        software.atlas = make_path_type("atlas", ATLAS_DIR, ATLAS_PATTERN)
        software.save()
        group = ScreenSessionGroup.objects.create(name="grp1", session_plan=session_plan)
        return AtlasSession.objects.create(name="scrn1", group=group)

    def test_substitutes_group_and_atlas_session_tokens(self, atlas_session):
        assert atlas_session.get_session_dir("atlas").endswith("/tomo/grp1/scrn1/Atlas/")

    def test_nothing_is_left_unsubstituted(self, atlas_session):
        assert "{" not in atlas_session.get_session_dir("atlas")

    def test_returns_dot_when_software_role_is_null(self, db, session_plan):
        session_plan.software.atlas = None
        session_plan.software.save()
        group = ScreenSessionGroup.objects.create(name="grp2", session_plan=session_plan)
        atlas = AtlasSession.objects.create(name="scrn2", group=group)
        assert atlas.get_session_dir("atlas") == "."

    def test_a_linked_atlas_supplies_the_screening_plans_pattern(self, atlas_session, msi_session):
        """`atlas` is the one role whose directory comes from another plan, so its pattern
        has to come from the same place."""
        msi_session.atlas_session = atlas_session
        msi_session.save()
        assert msi_session.get_file_pattern("atlas").list_glob == "Atlas_*.mrc"

    def test_a_linked_atlas_is_inherited_rather_than_resolved(self, atlas_session, msi_session):
        """The session reuses the screening session's row: resolving one of its own would
        point it at a directory no screening ever wrote to."""
        atlas_session.atlas = atlas_session.resolve_path_row("atlas")
        atlas_session.save()
        msi_session.atlas_session = atlas_session

        msi_session.resolve_role_paths()

        assert msi_session.atlas == atlas_session.atlas
