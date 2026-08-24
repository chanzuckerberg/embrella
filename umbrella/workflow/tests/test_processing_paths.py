"""Processing path roots come from the database, entered by admin in Stores / Paths"""

import pytest
from django.core.exceptions import ImproperlyConfigured
from processes.models import ProcSoftware
from workflow.processors import get_processor

pytestmark = pytest.mark.django_db


def given_software(processor_class, *, script_directory="", processing_directory="", storage_dirname="", name=None):
    obj, _ = ProcSoftware.objects.update_or_create(
        processor_class=processor_class,
        defaults={
            "name": name or processor_class,
            "script_directory": script_directory,
            "processing_directory": processing_directory,
            "storage_dirname": storage_dirname,
        },
    )
    return obj


class TestPathsComeFromTheDatabase:
    def test_each_directory_is_read_from_its_own_field(self):
        given_software(
            "aretomo3",
            processing_directory="/hpc/projects/group.czii/krios1.processing/aretomo3",
            script_directory="/hpc/projects/group.czii/krios1.processing/aretomo3/scripts",
        )
        p = get_processor("aretomo3")
        assert p.get_processing_base_path() == "/hpc/projects/group.czii/krios1.processing/aretomo3"
        assert p.get_script_directory() == "/hpc/projects/group.czii/krios1.processing/aretomo3/scripts"

    def test_updating_entry(self):
        """The point of reading the DB."""
        given_software("aretomo3", processing_directory="/data/elsewhere/aretomo3")
        assert get_processor("aretomo3").get_processing_base_path() == "/data/elsewhere/aretomo3"

    def test_processing_and_script_directories_can_be_different(self):
        """When root and scripts are stored in different places."""
        given_software(
            "aretomo3",
            processing_directory="/data/runs/aretomo3",
            script_directory="/shared/software/scripts/aretomo3",
        )
        p = get_processor("aretomo3")
        assert p.get_processing_base_path() == "/data/runs/aretomo3"
        assert p.get_script_directory() == "/shared/software/scripts/aretomo3"

    def test_trailing_slash_does_not_produce_an_empty_segment(self):
        given_software("aretomo3", processing_directory="/data/aretomo3/")
        assert get_processor("aretomo3").get_processing_base_path() == "/data/aretomo3"


class TestTheCasesTheOverridesExistedFor:
    """Before the paths were derived from software name. Now should be explicitly set in db"""

    def test_denoiset_writes_into_denoise(self):
        """The processor class is `denoiset`; the directory is `denoise`."""
        given_software(
            "denoiset",
            name="denoise",
            processing_directory="/hpc/projects/group.czii/krios1.processing/denoise",
        )
        assert get_processor("denoiset").get_processing_base_path() == (
            "/hpc/projects/group.czii/krios1.processing/denoise"
        )

    @pytest.mark.parametrize("processor_class", ["copick-import", "copick-add-object"])
    def test_copick_accessories_share_the_copick_directory(self, processor_class):
        given_software(processor_class, processing_directory="/hpc/projects/group.czii/krios1.processing/copick")
        assert get_processor(processor_class).get_processing_base_path() == (
            "/hpc/projects/group.czii/krios1.processing/copick"
        )


class TestUnconfiguredIsAnError:
    """There is no fallback root. Guessing one would put this deployment's paths in
    everyone else's install, and would fail at job submission rather than at setup."""

    def test_unset_processing_directory_raises(self):
        given_software("denoiset", name="denoise", storage_dirname="denoise")
        with pytest.raises(ImproperlyConfigured, match="processing_directory is unset for 'denoiset'"):
            get_processor("denoiset").get_processing_base_path()

    def test_no_row_at_all_raises(self):
        ProcSoftware.objects.filter(processor_class="aretomo3").delete()
        with pytest.raises(ImproperlyConfigured, match="Processes → Proc softwares"):
            get_processor("aretomo3").get_processing_base_path()

    def test_unset_script_directory_raises(self):
        """The fields fail independently: a configured root does not excuse a blank
        script directory, which the old parent-derivation would have hidden."""
        given_software("aretomo3", processing_directory="/data/aretomo3", script_directory="")
        with pytest.raises(ImproperlyConfigured, match="script_directory is unset"):
            get_processor("aretomo3").get_script_directory()
