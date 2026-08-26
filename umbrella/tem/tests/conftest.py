"""
Shared fixtures for tem tests.
"""

import pytest
from cryo_grids.models import CryoGrid
from django.contrib.auth.models import User
from projects.models import Project
from stores.models import DataKind, FilePattern, PathType

from tem.models import (
    Camera,
    ImagingWorkflow,
    Magnification,
    Microscope,
    SessionPlan,
    Software,
)


@pytest.fixture
def test_user(db):
    return User.objects.create_user(username="testuser", password="testpass")


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
def software(db):
    return Software.objects.create(name="TestSoftware")


@pytest.fixture
def session_plan(db, microscope, camera, software):
    imaging_workflow = ImagingWorkflow.objects.create(imaging_mode="tem", workflow="tomo")
    return SessionPlan.objects.create(
        scope=microscope,
        camera=camera,
        imaging_workflow=imaging_workflow,
        software=software,
    )


@pytest.fixture
def plan_with_frames(db, session_plan):
    """The shared plan, with `frames` given a split directory template and its file pattern."""
    kind = DataKind.objects.create(data_type="frames")
    session_plan.software.frames = PathType.objects.create(
        data_kind=kind,
        overlay_path="/hpc/instruments/czii.{scope}/OffloadData/{msi_session}/",
        file_pattern=FilePattern.objects.create(
            data_kind=kind,
            label="{run}_{sequence}_{tilt}_*.eer",
            list_glob="*.eer",
            regex=r"^(?P<run>.+)_(?P<sequence>\d+)_(?P<tilt>-?\d+(?:\.\d+)?)_.*\.eer$",
        ),
    )
    session_plan.software.save()
    return session_plan


@pytest.fixture
def project(db):
    return Project.objects.create(name="TestProject")


@pytest.fixture
def grid(db):
    return CryoGrid.objects.create(name="TestGrid")
