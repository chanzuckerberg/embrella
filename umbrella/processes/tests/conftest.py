"""
Shared fixtures for processes tests.
"""

import pytest
from tem.models import Camera, ImagingWorkflow, Microscope, SessionPlan, Software


@pytest.fixture
def session_plan(db):
    """The minimum required to create an MsiSession (session_plan is non-null)."""
    return SessionPlan.objects.create(
        scope=Microscope.objects.create(name="TestScope", cs=2.7),
        camera=Camera.objects.create(
            name="TestCam",
            root_dir="/test/root",
            frame_format="eer",
            initial_frame_base_dir="/test/frames",
        ),
        imaging_workflow=ImagingWorkflow.objects.create(imaging_mode="tem", workflow="tomo"),
        software=Software.objects.create(name="TestCollectionSoftware"),
    )
