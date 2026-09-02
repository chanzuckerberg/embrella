"""Per-plan path bindings: allows 2 or more different scopes with same software to resolve to different directories."""

import pytest
from django.db.utils import IntegrityError
from stores.models import Cluster, DataKind, FilePattern, Path, PathType, pick_for_cluster

from tem.models import (
    SOFTWARE_PATH_ROLES,
    TILT_SERIES_ROLE,
    Camera,
    ImagingWorkflow,
    Microscope,
    MsiSession,
    SessionPlan,
    SessionPlanPathBinding,
    Software,
    resolve_plan_file_pattern,
    resolve_software_file_pattern,
    resolve_software_path_type,
)

KRIOS_FRAMES = "/hpc/instruments/czii.{scope}/OffloadData/{msi_session}/"
OTHER_TEST_FRAMES = "/data/{scope}/frames/{msi_session}/"


def make_path_type(data_type, overlay_path, cluster=None):
    kind, _ = DataKind.objects.get_or_create(data_type=data_type)
    return PathType.objects.create(data_kind=kind, overlay_path=overlay_path, cluster=cluster)


def make_file_pattern(list_glob, regex=r"^(?P<run>\w+)\.eer$"):
    kind, _ = DataKind.objects.get_or_create(data_type="frames")
    return FilePattern.objects.create(data_kind=kind, label=list_glob, list_glob=list_glob, regex=regex)


def attach_pattern(path_type, list_glob, **kwargs):
    """Give `path_type` its default FilePattern, and return the pattern."""
    path_type.file_pattern = make_file_pattern(list_glob, **kwargs)
    path_type.save(update_fields=["file_pattern"])
    return path_type.file_pattern


@pytest.fixture
def camera(db):
    return Camera.objects.create(
        name="Falcon4i", root_dir="/hpc/x/", frame_format="eer", initial_frame_base_dir="/OffloadData/"
    )


@pytest.fixture
def workflow(db):
    return ImagingWorkflow.objects.create(imaging_mode="tem", workflow="tomo")


@pytest.fixture
def software(db):
    """One software, serving both scopes."""
    return Software.objects.create(name="tomo5", frames=make_path_type("frames", KRIOS_FRAMES))


def make_plan(scope_name, camera, workflow, software):
    return SessionPlan.objects.create(
        scope=Microscope.objects.create(name=scope_name, cs=2.7),
        camera=camera,
        imaging_workflow=workflow,
        software=software,
    )


@pytest.mark.django_db
class TestTheFeature:
    def test_two_scopes_resolve_to_different_directories(self, camera, workflow, software):
        """One software, two scopes, one binding row -- and sessions on each plan
        auto-populate different paths with no per-session work."""
        krios = make_plan("krios1", camera, workflow, software)
        other = make_plan("other2", camera, workflow, software)
        SessionPlanPathBinding.objects.create(
            session_plan=other, role="frames", path_type=make_path_type("frames", OTHER_TEST_FRAMES)
        )

        a = MsiSession.objects.create(name="24nov10", session_plan=krios)
        b = MsiSession.objects.create(name="24nov11", session_plan=other)

        assert a._resolve_path_row("frames").overlay_path == "/hpc/instruments/czii.krios1/OffloadData/24nov10/"
        assert b._resolve_path_row("frames").overlay_path == "/data/other2/frames/24nov11/"

    def test_creating_a_session_writes_no_bindings(self, camera, workflow, software):
        """Bindings scale with plans, not sessions."""
        plan = make_plan("krios1", camera, workflow, software)
        MsiSession.objects.create(name="24nov10", session_plan=plan)._resolve_path_row("frames")
        assert SessionPlanPathBinding.objects.count() == 0


@pytest.mark.django_db
class TestResolutionChain:
    def test_software_default_when_no_binding(self, camera, workflow, software):
        plan = make_plan("krios1", camera, workflow, software)
        assert resolve_software_path_type(plan, "frames") == software.frames

    def test_binding_wins_over_default(self, camera, workflow, software):
        plan = make_plan("krios1", camera, workflow, software)
        override = make_path_type("frames", OTHER_TEST_FRAMES)
        SessionPlanPathBinding.objects.create(session_plan=plan, role="frames", path_type=override)
        assert resolve_software_path_type(plan, "frames") == override

    def test_inactive_binding_is_ignored(self, camera, workflow, software):
        plan = make_plan("krios1", camera, workflow, software)
        SessionPlanPathBinding.objects.create(
            session_plan=plan, role="frames", path_type=make_path_type("frames", OTHER_TEST_FRAMES), is_active=False
        )
        assert resolve_software_path_type(plan, "frames") == software.frames

    def test_binding_with_no_path_type_falls_through(self, camera, workflow, software):
        """A row exists but overrides nothing -- still the default, not None."""
        plan = make_plan("krios1", camera, workflow, software)
        SessionPlanPathBinding.objects.create(session_plan=plan, role="frames", path_type=None)
        assert resolve_software_path_type(plan, "frames") == software.frames

    def test_none_when_software_does_not_emit_the_role(self, camera, workflow, software):
        """NULL on the software is terminal: this software produces no sums at all."""
        plan = make_plan("krios1", camera, workflow, software)
        assert resolve_software_path_type(plan, "sums") is None

    def test_one_binding_per_plan_and_role(self, camera, workflow, software):
        plan = make_plan("krios1", camera, workflow, software)
        SessionPlanPathBinding.objects.create(session_plan=plan, role="frames", path_type=None)
        with pytest.raises(IntegrityError):
            SessionPlanPathBinding.objects.create(session_plan=plan, role="frames", path_type=None)


@pytest.mark.django_db
class TestNoBackfillRegression:
    def test_zero_bindings_resolves_exactly_as_before(self, camera, workflow, software):
        """A single-scope install has no bindings, so every role must resolve to the
        software default byte-identically -- that is what makes Phase 1 backfill-free."""
        plan = make_plan("krios1", camera, workflow, software)
        expected = {"frames": software.frames, "sums": None, "mdocs": None, "parents": None, "atlas": None}
        for role in SOFTWARE_PATH_ROLES:
            assert resolve_software_path_type(plan, role) == expected[role]


@pytest.mark.django_db
class TestRoleMappings:
    def test_every_role_is_a_software_field(self, software):
        assert software.role_path_types.keys() == set(SOFTWARE_PATH_ROLES)

    def test_every_role_is_a_session_field(self, camera, workflow, software):
        session = MsiSession.objects.create(name="24nov10", session_plan=make_plan("k1", camera, workflow, software))
        assert session.role_paths.keys() == set(SOFTWARE_PATH_ROLES)

    def test_resolve_role_paths_leaves_an_unemitted_role_alone(self, camera, workflow, software):
        """This software has no sums template, so a Path attached by hand survives: absence
        of a template means "produces no such data", not "clear the field"."""
        session = MsiSession.objects.create(name="24nov10", session_plan=make_plan("k1", camera, workflow, software))
        session.sums = Path.objects.create(overlay_path="/set/by/hand/")

        session.resolve_role_paths()

        assert session.sums.overlay_path == "/set/by/hand/"
        assert session.frames.overlay_path == "/hpc/instruments/czii.k1/OffloadData/24nov10/"


@pytest.mark.django_db
class TestFilePatternResolution:
    """Directory and filename override on independent rungs -- the case that forced it being
    two scopes sharing a directory and naming their files differently."""

    def test_falls_back_to_directory(self, camera, workflow, software):
        plan = make_plan("krios1", camera, workflow, software)
        default = attach_pattern(software.frames, "*.eer")
        assert resolve_software_file_pattern(plan, "frames") == default

    def test_binding_overrides_filename(self, camera, workflow, software):
        plan = make_plan("krios2", camera, workflow, software)
        attach_pattern(software.frames, "*.eer")
        theirs = make_file_pattern("*.tif", regex=r"^(?P<position>\d+)\.tif$")
        SessionPlanPathBinding.objects.create(session_plan=plan, role="frames", file_pattern=theirs)

        assert resolve_software_file_pattern(plan, "frames") == theirs
        assert resolve_software_path_type(plan, "frames") == software.frames

    def test_new_directory_brings_pattern(self, camera, workflow, software):
        plan = make_plan("krios2", camera, workflow, software)
        elsewhere = make_path_type("frames", OTHER_TEST_FRAMES)
        pattern = attach_pattern(elsewhere, "*.tif")
        SessionPlanPathBinding.objects.create(session_plan=plan, role="frames", path_type=elsewhere)

        assert resolve_software_file_pattern(plan, "frames") == pattern

    def test_none_when_no_pattern(self, camera, workflow, software):
        """The state of every row today: patterns are additive, so none must stay legal."""
        plan = make_plan("krios1", camera, workflow, software)
        assert resolve_software_file_pattern(plan, "frames") is None

    def test_none_when_role_unsupported(self, camera, workflow, software):
        plan = make_plan("krios1", camera, workflow, software)
        assert resolve_software_file_pattern(plan, "atlas") is None


@pytest.mark.django_db
class TestTiltSeriesBinding:
    """tilt_series is pattern-only: it holds the plan's own output naming for the
    processing lane to read -- there is no Software field rung."""

    def make_rec_pattern(self):
        kind, _ = DataKind.objects.get_or_create(data_type="rec")
        return FilePattern.objects.create(
            data_kind=kind, label="serialEM rec", regex=r"^(?P<position>\w+_ts_\d+)\.mrc_Vol\.zarr$"
        )

    def test_resolves_the_bound_pattern(self, camera, workflow, software):
        plan = make_plan("krios2", camera, workflow, software)
        pattern = self.make_rec_pattern()
        SessionPlanPathBinding.objects.create(session_plan=plan, role=TILT_SERIES_ROLE, file_pattern=pattern)

        assert resolve_plan_file_pattern(plan, TILT_SERIES_ROLE) == pattern

    def test_none_without_binding(self, camera, workflow, software):
        plan = make_plan("krios1", camera, workflow, software)
        assert resolve_plan_file_pattern(plan, TILT_SERIES_ROLE) is None

    def test_inactive_binding_is_ignored(self, camera, workflow, software):
        plan = make_plan("krios2", camera, workflow, software)
        SessionPlanPathBinding.objects.create(
            session_plan=plan, role=TILT_SERIES_ROLE, file_pattern=self.make_rec_pattern(), is_active=False
        )
        assert resolve_plan_file_pattern(plan, TILT_SERIES_ROLE) is None

    def test_role_is_a_legal_choice(self, camera, workflow, software):
        plan = make_plan("krios2", camera, workflow, software)
        binding = SessionPlanPathBinding(session_plan=plan, role=TILT_SERIES_ROLE, file_pattern=self.make_rec_pattern())
        binding.full_clean()  # raises on an unknown role choice

    def test_not_a_software_field_role(self):
        """Guards the double-duty tuple: Software must not grow a tilt_series FK.
        software currently only has 5 FKs, and tilt_series is not one of them currently."""
        assert TILT_SERIES_ROLE not in SOFTWARE_PATH_ROLES


@pytest.mark.django_db
class TestClusterSelection:
    def test_prefers_the_cluster_specific_row(self):
        czii = Cluster.objects.create(cluster_id="c1", name="C1", http_base_url="https://a/", ssh_hostname="h")
        default = make_path_type("rec", "/default/")
        specific = make_path_type("rec", "/on-c1/", cluster=czii)
        assert pick_for_cluster([default, specific], czii) == specific

    def test_falls_back_to_the_agnostic_default(self):
        other = Cluster.objects.create(cluster_id="c2", name="C2", http_base_url="https://b/", ssh_hostname="h")
        default = make_path_type("rec", "/default/")
        assert pick_for_cluster([default], other) == default

    def test_none_when_nothing_matches(self):
        czii = Cluster.objects.create(cluster_id="c1", name="C1", http_base_url="https://a/", ssh_hostname="h")
        assert pick_for_cluster([make_path_type("rec", "/on-c1/", cluster=czii)], None) is None

    def test_resolve_uses_the_cluster(self):
        czii = Cluster.objects.create(cluster_id="c1", name="C1", http_base_url="https://a/", ssh_hostname="h")
        make_path_type("rec", "/default/")
        specific = make_path_type("rec", "/on-c1/", cluster=czii)
        assert PathType.resolve("rec", cluster=czii) == specific
        assert PathType.resolve("rec").overlay_path == "/default/"
