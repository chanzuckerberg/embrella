import datetime

import pytest
from django.utils import timezone

from tem.models import (
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
