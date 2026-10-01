import datetime

import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone

from tem.models import (
    AcquisitionSettings,
    CalibratedPixelSize,
    Camera,
    ImagingWorkflow,
    Magnification,
    Microscope,
    MsiSession,
    SessionPlan,
    Software,
)


@pytest.fixture
def microscope(db):
    return Microscope.objects.create(name="TestScope", cs=2.7)


@pytest.fixture
def camera(db):
    return Camera.objects.create(
        name="TestCam",
        root_dir="/test/root",
        frame_format="eer",
        initial_frame_base_dir="/test/frames",
    )


@pytest.fixture
def magnification(db, microscope):
    return Magnification.objects.create(scope=microscope, mode="SA", nominal_mag=50000, index=0)


@pytest.fixture
def session_plan(db, microscope, camera):
    imaging_workflow = ImagingWorkflow.objects.create(imaging_mode="tem", workflow="tomo")
    software = Software.objects.create(name="TestSoftware")
    return SessionPlan.objects.create(
        scope=microscope,
        camera=camera,
        imaging_workflow=imaging_workflow,
        software=software,
    )


@pytest.fixture
def msi_session(db, session_plan, magnification):
    return MsiSession.objects.create(
        name="26mar05a",
        session_plan=session_plan,
        magnification=magnification,
    )


@pytest.mark.django_db
class TestGetCalibratedPixelSize:
    def test_returns_pixel_size_when_calibration_exists(self, msi_session, magnification, camera):
        CalibratedPixelSize.objects.create(
            mag=magnification,
            camera=camera,
            pixel_spacing=1.54,
            calibrated_at=timezone.now(),
        )
        assert msi_session.get_calibrated_pixel_size() == 1.54

    def test_returns_none_when_no_magnification(self, session_plan):
        session = MsiSession.objects.create(
            name="26mar05b",
            session_plan=session_plan,
            magnification=None,
        )
        assert session.get_calibrated_pixel_size() is None

    def test_returns_none_when_no_calibration(self, msi_session):
        assert msi_session.get_calibrated_pixel_size() is None

    def test_returns_most_recent_calibration(self, msi_session, magnification, camera):
        CalibratedPixelSize.objects.create(
            mag=magnification,
            camera=camera,
            pixel_spacing=2.00,
            calibrated_at=datetime.datetime(2024, 1, 1, tzinfo=datetime.timezone.utc),
        )
        CalibratedPixelSize.objects.create(
            mag=magnification,
            camera=camera,
            pixel_spacing=1.54,
            calibrated_at=datetime.datetime(2025, 6, 1, tzinfo=datetime.timezone.utc),
        )
        assert msi_session.get_calibrated_pixel_size() == 1.54

    def test_ignores_calibration_for_different_camera(self, msi_session, magnification):
        other_camera = Camera.objects.create(
            name="OtherCam",
            root_dir="/other/root",
            frame_format="tiff",
            initial_frame_base_dir="/other/frames",
        )
        CalibratedPixelSize.objects.create(
            mag=magnification,
            camera=other_camera,
            pixel_spacing=5.0,
            calibrated_at=timezone.now(),
        )
        assert msi_session.get_calibrated_pixel_size() is None

    def test_ignores_calibration_for_different_magnification(self, msi_session, microscope, camera):
        other_mag = Magnification.objects.create(scope=microscope, mode="SA", nominal_mag=80000, index=1)
        CalibratedPixelSize.objects.create(
            mag=other_mag,
            camera=camera,
            pixel_spacing=1.5,
            calibrated_at=timezone.now(),
        )
        assert msi_session.get_calibrated_pixel_size() is None


@pytest.mark.django_db
class TestSessionPlanNamePrefix:
    def test_defaults_to_blank(self, session_plan):
        assert session_plan.name_prefix == ""

    @pytest.mark.parametrize("prefix", ["", "s", "abcd"])
    def test_accepts_lowercase_letters(self, session_plan, prefix):
        session_plan.name_prefix = prefix
        session_plan.full_clean()

    @pytest.mark.parametrize("prefix", ["S", "s1", "s-", "abcde"])
    def test_rejects_anything_else(self, session_plan, prefix):
        session_plan.name_prefix = prefix
        with pytest.raises(ValidationError):
            session_plan.full_clean()


@pytest.mark.django_db
class TestAcquisitionSettings:
    def test_plan_without_profile_reports_field_defaults(self, session_plan):
        assert session_plan.acquisition_values() == {
            "super_resolution": False,
            "phase_plate_used": False,
            "energy_filter_used": False,
        }

    def test_snapshot_copies_then_overrides(self):
        profile = AcquisitionSettings.objects.create(label="krios2", super_resolution=True)

        copy = profile.snapshot("snapshot 26sep15a")
        assert copy.values() == {"super_resolution": True, "phase_plate_used": False, "energy_filter_used": False}
        assert str(copy) == "snapshot 26sep15a"
        assert profile.snapshot("x", super_resolution=False).values() == {
            "super_resolution": False,
            "phase_plate_used": False,
            "energy_filter_used": False,
        }

    def test_snapshot_does_not_alias_the_profile(self, msi_session):
        profile = AcquisitionSettings.objects.create(label="krios2", super_resolution=True)
        msi_session.acquisition = profile.snapshot(AcquisitionSettings.snapshot_label(msi_session.name))
        msi_session.save()

        profile.super_resolution = False
        profile.save()

        msi_session.refresh_from_db()
        assert msi_session.acquisition.pk != profile.pk
        assert msi_session.super_resolution is True

    def test_session_without_row_is_not_super_resolution(self, msi_session):
        assert msi_session.super_resolution is False
