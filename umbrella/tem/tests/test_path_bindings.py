"""Per-plan path bindings: allows 2 or more different scopes with same software to resolve to different directories."""

import pytest
from django.db.utils import IntegrityError
from stores.models import Cluster, DataKind, PathType, pick_for_cluster

from tem.models import (
    SOFTWARE_PATH_ROLES,
    Camera,
    ImagingWorkflow,
    Microscope,
    MsiSession,
    SessionPlan,
    SessionPlanPathBinding,
    Software,
    resolve_software_path_type,
)

KRIOS_FRAMES = "/hpc/instruments/czii.{scope}/OffloadData/{msi_session}/"
OTHER_TEST_FRAMES = "/data/{scope}/frames/{msi_session}/"


def make_path_type(data_type, overlay_path, cluster=None):
    kind, _ = DataKind.objects.get_or_create(data_type=data_type)
    return PathType.objects.create(data_kind=kind, overlay_path=overlay_path, cluster=cluster)


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

        assert a.get_session_path("frames").overlay_path == "/hpc/instruments/czii.krios1/OffloadData/24nov10/"
        assert b.get_session_path("frames").overlay_path == "/data/other2/frames/24nov11/"

    def test_creating_a_session_writes_no_bindings(self, camera, workflow, software):
        """Bindings scale with plans, not sessions."""
        plan = make_plan("krios1", camera, workflow, software)
        MsiSession.objects.create(name="24nov10", session_plan=plan).get_session_path("frames")
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
        for role in SOFTWARE_PATH_ROLES:
            assert resolve_software_path_type(plan, role) == getattr(software, role)


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
