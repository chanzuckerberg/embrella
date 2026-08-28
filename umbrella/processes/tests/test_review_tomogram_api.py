"""The tomogram detail zarrPath replays what the syncer discovered.

The URL is the resolved zarr_url directory plus ReviewTomogram.file_path -- no filename
convention is re-derived here, so scopes/software with other naming schemes just work.
"""

from unittest.mock import patch

import pytest
from django.contrib.auth.models import User
from django.test import override_settings
from stores.models import Cluster
from tem.models import Camera, ImagingWorkflow, Microscope, MsiSession, SessionPlan, Software

from processes.models import Review, ReviewTomogram

pytestmark = pytest.mark.django_db

FILESERVER = "https://files.example"


@pytest.fixture
def review_tomogram(db):
    plan = SessionPlan.objects.create(
        scope=Microscope.objects.create(name="krios1", cs=2.7),
        camera=Camera.objects.create(
            name="TestCam", root_dir="/test/root", frame_format="eer", initial_frame_base_dir="/test/frames"
        ),
        imaging_workflow=ImagingWorkflow.objects.create(imaging_mode="tem", workflow="tomo"),
        software=Software.objects.create(name="tomo5"),
    )
    session = MsiSession.objects.create(name="25aug25a", session_plan=plan)
    cluster = Cluster.objects.create(
        cluster_id="testcluster", name="Test", http_base_url=f"{FILESERVER}/", ssh_hostname="hpc"
    )
    review = Review.objects.create(
        review_name="sart review",
        review_type="tomogram_quality",
        run_id="run003",
        reconstruction_type="SART",
        msi_session=session,
        cluster=cluster,
    )
    return ReviewTomogram.objects.create(
        tomogram_id="demo-tomo-1",
        session=session,
        review=review,
        run_id="run003",
        reconstruction_type="SART",
        position_id="Position_1",
        file_path="vol003/Position_1_Vol.zarr",
    )


@override_settings(FILESERVER_ALLOWED_HOSTS=[FILESERVER])
@patch("processes.api.views.compute_optimal_contrast_limits", return_value=(0.0, 1.0))
def test_zarr_path_appends_the_stored_file_path(_contrast, client, review_tomogram):
    client.force_login(User.objects.create_user(username="reviewer"))
    url = f"/api/reviews/{review_tomogram.review.review_id}/tomograms/{review_tomogram.tomogram_id}"

    response = client.get(url)

    assert response.status_code == 200
    assert response.json()["zarrPath"] == (
        f"{FILESERVER}/krios1.processing/aretomo3/25aug25a/run003/vol003/Position_1_Vol.zarr"
    )
