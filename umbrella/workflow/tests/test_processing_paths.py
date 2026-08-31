"""Processing path roots resolve from the processing_root / script_dir templates.

One constant tree serves every scope; {proc_software} is the only substitution.
"""

from types import SimpleNamespace

import pytest
from django.core.exceptions import ImproperlyConfigured
from processes.models import ProcSoftware
from stores.models import DataKind, FilePattern, PathType
from stores.paths import UnresolvedPlaceholderError
from tem.models import (
    TILT_SERIES_ROLE,
    Camera,
    ImagingWorkflow,
    Microscope,
    SessionPlan,
    SessionPlanPathBinding,
    Software,
)
from workflow.processors import get_processor

pytestmark = pytest.mark.django_db

PROCESSING_ROOT = "/hpc/projects/group.czii/krios1.processing/{proc_software}"
SCRIPT_DIR = "/hpc/projects/group.czii/krios1.processing/{proc_software}/scripts"


@pytest.fixture
def templates(db):
    """The shipped template rows, replacing the migration-seeded ones."""
    for data_type, overlay in (("processing_root", PROCESSING_ROOT), ("script_dir", SCRIPT_DIR)):
        kind, _ = DataKind.objects.get_or_create(data_type=data_type)
        PathType.objects.filter(data_kind=kind).delete()
        PathType.objects.create(data_kind=kind, cluster=None, overlay_path=overlay)


def given_software(processor_class, *, storage_dirname="", name=None):
    obj, _ = ProcSoftware.objects.update_or_create(
        processor_class=processor_class,
        defaults={"name": name or processor_class, "storage_dirname": storage_dirname},
    )
    return obj


class TestSharedTemplates:
    def test_root_substitutes_the_software_dirname(self, templates):
        given_software("aretomo3")
        expected = "/hpc/projects/group.czii/krios1.processing/aretomo3"
        assert get_processor("aretomo3").get_processing_base_path() == expected

    def test_script_dir_resolves_from_its_own_template(self, templates):
        given_software("aretomo3")
        expected = "/hpc/projects/group.czii/krios1.processing/aretomo3/scripts"
        assert get_processor("aretomo3").get_script_directory() == expected

    def test_editing_the_template_moves_every_software(self, templates):
        """The point of reading the DB -- and why an adopter edits one row, not N columns."""
        given_software("aretomo3")
        PathType.objects.filter(data_kind__data_type="processing_root").update(
            overlay_path="/data/runs/{proc_software}"
        )
        assert get_processor("aretomo3").get_processing_base_path() == "/data/runs/aretomo3"


class TestPerSoftwareOverride:
    """software whose directories don't follow the standard layout."""

    def make_override(self, data_type, overlay_path):
        kind, _ = DataKind.objects.get_or_create(data_type=data_type)
        return PathType.objects.create(data_kind=kind, overlay_path=overlay_path)

    def test_override_row_wins_over_the_shared_template(self, templates):
        software = given_software("aretomo3")
        software.processing_root = self.make_override("processing_root", "/nonstandard/tree/{proc_software}")
        software.save()

        assert get_processor("aretomo3").get_processing_base_path() == "/nonstandard/tree/aretomo3"

    def test_script_dir_overrides_independently(self, templates):
        """A custom script location does not move the processing root."""
        software = given_software("aretomo3")
        software.script_dir = self.make_override("script_dir", "/shared/slurm_scripts/{proc_software}")
        software.save()

        p = get_processor("aretomo3")
        assert p.get_script_directory() == "/shared/slurm_scripts/aretomo3"
        assert p.get_processing_base_path() == "/hpc/projects/group.czii/krios1.processing/aretomo3"

    def test_blank_uses_the_shared_template(self, templates):
        given_software("aretomo3")
        expected = "/hpc/projects/group.czii/krios1.processing/aretomo3"
        assert get_processor("aretomo3").get_processing_base_path() == expected


class TestTheCasesTheOverridesExistedFor:
    """{proc_software} substitutes dirname, so the awkward names need no extra rows."""

    def test_denoiset_writes_into_denoise(self, templates):
        """The processor class is `denoiset`; the directory is `denoise`."""
        given_software("denoiset", name="denoise")
        assert get_processor("denoiset").get_processing_base_path() == (
            "/hpc/projects/group.czii/krios1.processing/denoise"
        )

    @pytest.mark.parametrize("processor_class", ["copick-import", "copick-add-object"])
    def test_copick_accessories_share_the_copick_directory(self, templates, processor_class):
        given_software(processor_class, storage_dirname="copick")
        assert get_processor(processor_class).get_processing_base_path() == (
            "/hpc/projects/group.czii/krios1.processing/copick"
        )


class TestSoftwareRoot:
    """One shared tools tree (stores/0022); no ProcSoftware row involved."""

    def test_resolves_from_the_seeded_template(self):
        expected = "/hpc/projects/group.czii/krios1.processing/software"
        assert get_processor("aretomo3").get_software_root() == expected

    def test_missing_row_raises(self):
        PathType.objects.filter(data_kind__data_type="software_root").delete()
        with pytest.raises(PathType.DoesNotExist, match="software_root"):
            get_processor("aretomo3").get_software_root()


class TestUnconfiguredIsAnError:
    """There is no fallback root. Guessing one would put this deployment's paths in
    everyone else's install, and would fail at job submission rather than at setup."""

    def test_missing_template_raises(self):
        # simulate an install that lost the row.
        PathType.objects.filter(data_kind__data_type="processing_root").delete()
        given_software("aretomo3")
        with pytest.raises(PathType.DoesNotExist, match="processing_root"):
            get_processor("aretomo3").get_processing_base_path()

    def test_no_software_row_raises(self, templates):
        ProcSoftware.objects.filter(processor_class="aretomo3").delete()
        with pytest.raises(ImproperlyConfigured, match="No ProcSoftware row"):
            get_processor("aretomo3").get_processing_base_path()

    def test_scope_token_is_no_longer_supplied(self, templates):
        """Processing trees stopped varying by scope; a row still saying {scope} fails
        loudly at resolve time, not by writing a brace into a remote path."""
        given_software("aretomo3")
        PathType.objects.filter(data_kind__data_type="processing_root").update(
            overlay_path="/data/{scope}/runs/{proc_software}"
        )
        with pytest.raises(UnresolvedPlaceholderError, match="scope"):
            get_processor("aretomo3").get_processing_base_path()


REC_LABEL = "{position}_Vol.zarr"


def bind_rec_pattern(software):
    software.output_patterns.add(FilePattern.objects.get(data_kind__data_type="rec", label=REC_LABEL))


# The serialEM naming: the stem varies per plan, the _Vol.zarr tail is a static match.
SERIALEM_REC_REGEX = r"^(?P<position>\w+_ts_\d+)\.mrc_Vol\.zarr$"
SERIALEM_ZARRS = [
    "Position_10_ts_001.mrc_Vol.zarr",
    "pt712_ts_001.mrc_Vol.zarr",
    "pt729_ts_001.mrc_Vol.zarr",
    "pt729_ts_002.mrc_Vol.zarr",
]


def given_plan():
    return SessionPlan.objects.create(
        scope=Microscope.objects.create(name="krios2", cs=2.7),
        camera=Camera.objects.create(
            name="TestCam", root_dir="/test/root", frame_format="eer", initial_frame_base_dir="/test/frames"
        ),
        imaging_workflow=ImagingWorkflow.objects.create(imaging_mode="tem", workflow="tomo"),
        software=Software.objects.create(name="serialEM"),
    )


def bind_plan_pattern(plan, data_type="rec"):
    kind, _ = DataKind.objects.get_or_create(data_type=data_type)
    pattern = FilePattern.objects.create(
        data_kind=kind, label="serialEM rec", list_glob="*_Vol.zarr", regex=SERIALEM_REC_REGEX
    )
    SessionPlanPathBinding.objects.create(session_plan=plan, role=TILT_SERIES_ROLE, file_pattern=pattern)
    return pattern


class TestOutputPattern:
    """Software declares its output naming; there is no fallback pattern for the same
    reason there is no fallback root."""

    def test_resolves_the_bound_pattern(self, templates):
        bind_rec_pattern(given_software("aretomo3"))
        assert get_processor("aretomo3").get_output_pattern("rec").label == "{position}_Vol.zarr"

    def test_unbound_kind_raises(self, templates):
        given_software("aretomo3")
        with pytest.raises(ImproperlyConfigured, match="'rec' output pattern"):
            get_processor("aretomo3").get_output_pattern("rec")

    def test_unregistered_kind_raises(self, templates):
        """A typo'd or missing DataKind fails as "register the kind", not "bind a pattern"."""
        given_software("aretomo3")
        with pytest.raises(ImproperlyConfigured, match="No DataKind 'thumb'"):
            get_processor("aretomo3").get_output_pattern("thumb")

    def test_plan_binding_wins_over_the_software_row(self, templates):
        """serialEM names stacks its own way; the plan's pattern reads them, while the
        canonical row reads none of them -- why the plan rung exists."""
        bind_rec_pattern(given_software("aretomo3"))
        plan = given_plan()
        theirs = bind_plan_pattern(plan)
        canonical = FilePattern.objects.get(data_kind__data_type="rec", label=REC_LABEL)

        pattern = get_processor("aretomo3").get_output_pattern("rec", plan=plan)

        assert pattern == theirs
        for zarr in SERIALEM_ZARRS:
            assert pattern.match(zarr)["position"] == zarr.removesuffix(".mrc_Vol.zarr")
            assert canonical.match(zarr) is None

    def test_plan_without_binding_uses_the_software_row(self, templates):
        bind_rec_pattern(given_software("aretomo3"))
        pattern = get_processor("aretomo3").get_output_pattern("rec", plan=given_plan())
        assert pattern.label == REC_LABEL

    def test_binding_of_another_kind_is_ignored(self, templates):
        """The binding self-keys on its pattern's data kind: a row naming some other kind
        of file must not hijack rec resolution."""
        bind_rec_pattern(given_software("aretomo3"))
        plan = given_plan()
        bind_plan_pattern(plan, data_type="rawst")

        pattern = get_processor("aretomo3").get_output_pattern("rec", plan=plan)

        assert pattern.label == REC_LABEL


class TestPathsUsed:
    """The snapshot execution.py freezes into PipeExecution.parameters["_paths_used"],
    so a run keeps its resolved config after the operator edits the template rows."""

    def test_snapshot_names_root_and_bound_patterns(self, templates):
        bind_rec_pattern(given_software("aretomo3"))
        info = get_processor("aretomo3").get_paths_used(SimpleNamespace(cluster_id=None, msi_session=None))
        assert info == {
            "processing_base_path": "/hpc/projects/group.czii/krios1.processing/aretomo3",
            "output_patterns": {"rec": "{position}_Vol.zarr"},
        }

    def test_software_without_patterns_snapshots_none(self, templates):
        given_software("denoiset")
        info = get_processor("denoiset").get_paths_used(SimpleNamespace(cluster_id=None, msi_session=None))
        assert info["output_patterns"] == {}

    def test_bound_plan_snapshots_its_own_label(self, templates):
        """The snapshot records what the run resolves, not just what the software binds."""
        bind_rec_pattern(given_software("aretomo3"))
        plan = given_plan()
        bind_plan_pattern(plan)
        context = SimpleNamespace(cluster_id=None, msi_session=SimpleNamespace(session_plan=plan))

        info = get_processor("aretomo3").get_paths_used(context)

        assert info["output_patterns"] == {"rec": "serialEM rec"}
