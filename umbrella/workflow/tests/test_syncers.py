"""The syncer records what discovery found: the run-relative file path."""

from unittest.mock import patch

import pytest
from processes.models import ProcSoftware, ReviewTomogram, SyncerLog
from stores.models import DataKind, FilePattern
from tem.models import (
    TILT_SERIES_ROLE,
    Camera,
    ImagingWorkflow,
    Microscope,
    MsiSession,
    SessionPlan,
    SessionPlanPathBinding,
    Software,
)
from workflow.syncers import ProcessSyncer, parse_zarr_filename

pytestmark = pytest.mark.django_db

REC_LABEL = "{position}_Vol.zarr"

# One discovered zarr, as ((basename, position_id) pairs, rejected basenames) from check_zarr_exists.
ONE_ZARR = ([("Position_1_Vol.zarr", "Position_1")], [])

# The same, for a scope whose acquisition names stacks the serialEM way.
SERIALEM_ZARR = ([("pt712_ts_001.mrc_Vol.zarr", "pt712_ts_001")], [])

# Freestyle stems: only the pipeline-appended .mrc_Vol.zarr tail is fixed.
SERIALEM_REC_REGEX = r"^(?P<position>.+)\.mrc_Vol\.zarr$"


@pytest.fixture
def msi_session(db):
    plan = SessionPlan.objects.create(
        scope=Microscope.objects.create(name="krios1", cs=2.7),
        camera=Camera.objects.create(
            name="TestCam", root_dir="/test/root", frame_format="eer", initial_frame_base_dir="/test/frames"
        ),
        imaging_workflow=ImagingWorkflow.objects.create(imaging_mode="tem", workflow="tomo"),
        software=Software.objects.create(name="tomo5"),
    )
    return MsiSession.objects.create(name="25aug25a", session_plan=plan)


def given_syncer(msi_session, tmp_path):
    """A ProcessSyncer for aretomo3, whose software row has the rec pattern bound."""
    software, _ = ProcSoftware.objects.update_or_create(processor_class="aretomo3", defaults={"name": "aretomo3"})
    software.output_patterns.add(FilePattern.objects.get(data_kind__data_type="rec", label=REC_LABEL))

    syncer = ProcessSyncer(base_path="/proc/aretomo3", log_dir=str(tmp_path))
    syncer.processor_name = "aretomo3"
    syncer.run_id = "run003"
    syncer.session_name = msi_session.name
    syncer.session = msi_session
    return syncer


class TestDiscoveredFilePath:
    @patch("workflow.syncers.check_zarr_exists", return_value=ONE_ZARR)
    def test_subdir_prefixes_the_stored_path(self, _check, msi_session, tmp_path):
        syncer = given_syncer(msi_session, tmp_path)
        syncer.process_zarr_directory("SART", "/proc/aretomo3/25aug25a/run003/vol003", rel_dir="vol003")

        assert ReviewTomogram.objects.get().file_path == "vol003/Position_1_Vol.zarr"

    @patch("workflow.syncers.check_zarr_exists", return_value=ONE_ZARR)
    def test_run_level_files_store_the_bare_name(self, _check, msi_session, tmp_path):
        """The denoise layout: zarrs sit directly under the run directory."""
        syncer = given_syncer(msi_session, tmp_path)
        syncer.process_zarr_directory("Denoised", "/proc/denoise/25aug25a/run003")

        assert ReviewTomogram.objects.get().file_path == "Position_1_Vol.zarr"

    @patch("workflow.syncers.check_zarr_exists", return_value=ONE_ZARR)
    def test_creation_log_records_path_and_pattern(self, _check, msi_session, tmp_path):
        syncer = given_syncer(msi_session, tmp_path)
        syncer.process_zarr_directory("SART", "/proc/aretomo3/25aug25a/run003/vol003", rel_dir="vol003")

        entry = SyncerLog.objects.get(action_type="tomogram_created")
        assert entry.metadata["file_path"] == "vol003/Position_1_Vol.zarr"
        assert entry.metadata["pattern"] == REC_LABEL

    @patch("workflow.syncers.check_zarr_exists", return_value=ONE_ZARR)
    def test_resync_leaves_existing_rows_alone(self, _check, msi_session, tmp_path):
        syncer = given_syncer(msi_session, tmp_path)
        for _pass in range(2):
            syncer.process_zarr_directory("SART", "/proc/aretomo3/25aug25a/run003/vol003", rel_dir="vol003")

        assert ReviewTomogram.objects.count() == 1


def serialem_pattern():
    kind, _ = DataKind.objects.get_or_create(data_type="rec")
    return FilePattern.objects.create(data_kind=kind, label="serialEM rec", regex=SERIALEM_REC_REGEX)


def bind_plan_pattern(plan):
    SessionPlanPathBinding.objects.create(session_plan=plan, role=TILT_SERIES_ROLE, file_pattern=serialem_pattern())


class TestFreestyleStem:
    """Operators name stacks as they like; the id is whatever precedes the fixed tail."""

    @pytest.mark.parametrize(
        "basename, position_id",
        [
            ("pt712_ts_001.mrc_Vol.zarr", "pt712_ts_001"),
            ("grid3-sq2_lamella_ts_004.mrc_Vol.zarr", "grid3-sq2_lamella_ts_004"),
            ("L2 cell 7.mrc_Vol.zarr", "L2 cell 7"),
        ],
    )
    def test_stem_is_the_id(self, basename, position_id):
        assert parse_zarr_filename(basename, pattern=serialem_pattern()) == position_id

    @pytest.mark.parametrize("basename", ["pt712_ts_001.mrc_EVN_Vol.zarr", "pt712_ts_001.mrc_ODD_Vol.zarr"])
    def test_half_volumes_rejected(self, basename):
        assert parse_zarr_filename(basename, pattern=serialem_pattern()) is None


class TestUnmatchedWarning:
    @patch("workflow.syncers.check_zarr_exists", return_value=(ONE_ZARR[0], ["odd_name.zarr", "other.zarr"]))
    def test_names_the_rejects(self, _check, msi_session, tmp_path):
        syncer = given_syncer(msi_session, tmp_path)
        syncer.process_zarr_directory("SART", "/proc/aretomo3/25aug25a/run003/vol003", rel_dir="vol003")

        entry = SyncerLog.objects.get(action_type="warning")
        assert entry.message.startswith("2 of 3 .zarr entries")
        assert entry.metadata["examples"] == ["odd_name.zarr", "other.zarr"]
        assert entry.metadata["pattern"] == FilePattern.objects.get(label=REC_LABEL).regex


class TestPlanBoundPattern:
    """The session plan's own rec naming wins over the software's row, so a scope with
    its own acquisition naming syncs without touching the shared row."""

    @patch("workflow.syncers.check_zarr_exists", return_value=SERIALEM_ZARR)
    def test_syncer_matches_with_the_plans_pattern(self, _check, msi_session, tmp_path):
        bind_plan_pattern(msi_session.session_plan)
        syncer = given_syncer(msi_session, tmp_path)
        syncer.process_zarr_directory("SART", "/proc/aretomo3/25aug25a/run003/vol003", rel_dir="vol003")

        pattern = _check.call_args.args[1]
        assert pattern.regex == SERIALEM_REC_REGEX

        entry = SyncerLog.objects.get(action_type="tomogram_created")
        assert entry.metadata["pattern"] == "serialEM rec"
