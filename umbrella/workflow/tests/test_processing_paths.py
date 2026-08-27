"""Processing path roots resolve from the processing_root / script_dir templates.

These test resolution, scope-varying included.
"""

import pytest
from django.core.exceptions import ImproperlyConfigured
from processes.models import ProcSoftware
from stores.models import DataKind, PathType
from stores.paths import UnresolvedPlaceholderError
from workflow.processors import get_processor

pytestmark = pytest.mark.django_db

PROCESSING_ROOT = "/hpc/projects/group.czii/{scope}.processing/{proc_software}"
SCRIPT_DIR = "/hpc/projects/group.czii/{scope}.processing/{proc_software}/scripts"


@pytest.fixture
def templates(db):
    """Scope-varying template rows"""
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


class TestScopeAwareRoots:
    def test_scope_is_a_substitution_not_a_column(self, templates):
        """The point of the change: a second scope's roots need zero new config."""
        given_software("aretomo3")
        p = get_processor("aretomo3")
        assert p.get_processing_base_path(scope="krios1") == "/hpc/projects/group.czii/krios1.processing/aretomo3"
        assert p.get_processing_base_path(scope="krios2") == "/hpc/projects/group.czii/krios2.processing/aretomo3"

    def test_script_dir_resolves_from_its_own_template(self, templates):
        given_software("aretomo3")
        expected = "/hpc/projects/group.czii/krios1.processing/aretomo3/scripts"
        assert get_processor("aretomo3").get_script_directory(scope="krios1") == expected

    def test_editing_the_template_moves_every_software(self, templates):
        """The point of reading the DB -- and why an adopter edits one row, not N columns."""
        given_software("aretomo3")
        PathType.objects.filter(data_kind__data_type="processing_root").update(
            overlay_path="/data/{scope}/runs/{proc_software}"
        )
        assert get_processor("aretomo3").get_processing_base_path(scope="krios1") == "/data/krios1/runs/aretomo3"


class TestPerSoftwareOverride:
    """software whose directories don't follow the standard layout."""

    def make_override(self, data_type, overlay_path):
        kind, _ = DataKind.objects.get_or_create(data_type=data_type)
        return PathType.objects.create(data_kind=kind, overlay_path=overlay_path)

    def test_override_row_wins_over_the_shared_template(self, templates):
        software = given_software("aretomo3")
        software.processing_root = self.make_override("processing_root", "/nonstandard/tree/{proc_software}")
        software.save()

        assert get_processor("aretomo3").get_processing_base_path(scope="krios1") == "/nonstandard/tree/aretomo3"

    def test_script_dir_overrides_independently(self, templates):
        """A custom script location does not move the processing root."""
        software = given_software("aretomo3")
        software.script_dir = self.make_override("script_dir", "/shared/slurm_scripts/{proc_software}")
        software.save()

        p = get_processor("aretomo3")
        assert p.get_script_directory(scope="krios1") == "/shared/slurm_scripts/aretomo3"
        assert p.get_processing_base_path(scope="krios1") == "/hpc/projects/group.czii/krios1.processing/aretomo3"

    def test_blank_uses_the_shared_template(self, templates):
        given_software("aretomo3")
        expected = "/hpc/projects/group.czii/krios1.processing/aretomo3"
        assert get_processor("aretomo3").get_processing_base_path(scope="krios1") == expected


class TestTheCasesTheOverridesExistedFor:
    """{proc_software} substitutes dirname, so the awkward names need no extra rows."""

    def test_denoiset_writes_into_denoise(self, templates):
        """The processor class is `denoiset`; the directory is `denoise`."""
        given_software("denoiset", name="denoise")
        assert get_processor("denoiset").get_processing_base_path(scope="krios1") == (
            "/hpc/projects/group.czii/krios1.processing/denoise"
        )

    @pytest.mark.parametrize("processor_class", ["copick-import", "copick-add-object"])
    def test_copick_accessories_share_the_copick_directory(self, templates, processor_class):
        given_software(processor_class, storage_dirname="copick")
        assert get_processor(processor_class).get_processing_base_path(scope="krios1") == (
            "/hpc/projects/group.czii/krios1.processing/copick"
        )


class TestUnconfiguredIsAnError:
    """There is no fallback root. Guessing one would put this deployment's paths in
    everyone else's install, and would fail at job submission rather than at setup."""

    def test_missing_template_raises(self):
        # simulate an install that lost the row.
        PathType.objects.filter(data_kind__data_type="processing_root").delete()
        given_software("aretomo3")
        with pytest.raises(PathType.DoesNotExist, match="processing_root"):
            get_processor("aretomo3").get_processing_base_path(scope="krios1")

    def test_no_software_row_raises(self, templates):
        ProcSoftware.objects.filter(processor_class="aretomo3").delete()
        with pytest.raises(ImproperlyConfigured, match="No ProcSoftware row"):
            get_processor("aretomo3").get_processing_base_path(scope="krios1")

    def test_unresolved_token_raises(self, templates):
        """A template edit that adds a token nothing supplies fails loudly at resolve
        time, not by writing a brace into a remote path."""
        given_software("aretomo3")
        PathType.objects.filter(data_kind__data_type="processing_root").update(
            overlay_path="/data/{scope}/{msi_session}/{proc_software}"
        )
        with pytest.raises(UnresolvedPlaceholderError, match="msi_session"):
            get_processor("aretomo3").get_processing_base_path(scope="krios1")
