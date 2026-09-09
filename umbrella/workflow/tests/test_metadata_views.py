"""The metadata page resolves every remote location through the path system.

Directories come from the session's plan and the review templates; filenames follow
what mrc_to_zarr_and_thumbnails.sh writes (`{stem}.jpeg`, stem = Tilt_Series minus `.mrc`).
"""

import json
from unittest import mock

import pytest
from django.test import RequestFactory, override_settings
from stores.models import Cluster, DataKind, PathType
from workflow.views import metadata_views
from workflow.views.metadata_views import get_metadata_summary, get_metadata_viz_data

HTTP_BASE = "http://files.test/"
RUN_URL = HTTP_BASE + "krios1.processing/aretomo3/24nov10/run001/"

# One Tomo5 stack (`Position_13.mrc`) and one SerialEM stack whose stem keeps `.mrc`.
METRICS_CSV = """\
Tilt_Series,Thickness(Pix),Tilt_Axis,Global_Shift(Pix),Bad_Patch_Low,Bad_Patch_All,Defocus(A),ExtPhase(Deg),CTF_Res(A),CTF_Score,DF_Hand,Pix_Size(A),Cs(nm),Kv,Alpha0,Beta0
Position_13.mrc,1480,-95.97,118.12,0.00,0.00,49218.5,0.0,32.66,0.4901,1,3.70,2.7,300,15.5,-8.2
Position_8_ts_011.mrc.mrc,1260,-95.59,145.58,0.00,0.00,32287.8,0.0,8.26,0.1357,1,1.50,2.7,300,19.7,8.2
"""

pytestmark = pytest.mark.django_db


@pytest.fixture
def cluster(db):
    """The seeded default cluster (stores/0010), pointed at a test file server."""
    cluster, _ = Cluster.objects.update_or_create(
        cluster_id="czii",
        defaults={"name": "CZII", "http_base_url": HTTP_BASE, "ssh_hostname": "hpc", "is_default": True},
    )
    return cluster


@pytest.fixture
def frames_session(test_msi_session):
    """A session whose plan collects frames under a krios2-shaped instrument tree."""
    kind, _ = DataKind.objects.get_or_create(data_type="frames")
    software = test_msi_session.session_plan.software
    software.frames = PathType.objects.create(
        data_kind=kind,
        overlay_path="/hpc/instruments/czii.{scope}.k3/k3f/k3f_serialem/{msi_session}/",
    )
    software.save()
    return test_msi_session


@pytest.fixture
def metrics_csv():
    with mock.patch.object(metadata_views, "fetch_remote_text", return_value=METRICS_CSV) as fetch:
        yield fetch


def _call(view, **params):
    request = RequestFactory().get("/", params)
    with override_settings(FILESERVER_ALLOWED_HOSTS=[], FILESERVER_INTERNAL_BASE_URL=""):
        response = view(request)
    return response.status_code, json.loads(response.content)


class TestSummaryDirectories:
    def test_data_collection_dir_follows_the_plan(self, cluster, frames_session, metrics_csv):
        status, body = _call(get_metadata_summary, session_name="24nov10", run_number="run001")

        assert status == 200
        assert body["data_collection_directory"] == "/hpc/instruments/czii.TestScope.k3/k3f/k3f_serialem/24nov10/"
        assert body["aretomo3_processing_directory"] == (
            "/hpc/projects/group.czii/krios1.processing/aretomo3/24nov10/run001/"
        )
        metrics_csv.assert_called_once_with(RUN_URL + "TiltSeries_Metrics.csv")

    def test_no_frames_role_yields_null(self, cluster, test_msi_session, metrics_csv):
        status, body = _call(get_metadata_summary, session_name="24nov10", run_number="run001")

        assert status == 200
        assert body["data_collection_directory"] is None


class TestThumbnailNames:
    def test_stem_keeps_serialem_mrc(self, cluster, test_msi_session, metrics_csv):
        status, body = _call(get_metadata_viz_data, session_name="24nov10", run_number="run001")

        assert status == 200
        by_name = {item["name"]: item for item in body["accepted_results"] + body["rejected_results"]}
        assert set(by_name) == {"Position_13", "Position_8_ts_011.mrc"}

        assert by_name["Position_13"]["thumbnail_path"] == RUN_URL + "thumbnails/Position_13.jpeg"
        assert by_name["Position_13"]["ctf_path"] == RUN_URL + "ctf_thumbnails/Position_13.jpeg"
        serialem = by_name["Position_8_ts_011.mrc"]
        assert serialem["thumbnail_path"] == RUN_URL + "thumbnails/Position_8_ts_011.mrc.jpeg"
        assert serialem["ctf_path"] == RUN_URL + "ctf_thumbnails/Position_8_ts_011.mrc.jpeg"


class TestRunLookup:
    @pytest.mark.parametrize("view", [get_metadata_summary, get_metadata_viz_data])
    def test_missing_params(self, cluster, view):
        status, body = _call(view, session_name="24nov10")

        assert status == 400
        assert "error" in body

    @pytest.mark.parametrize("view", [get_metadata_summary, get_metadata_viz_data])
    def test_unknown_cluster(self, cluster, test_msi_session, view):
        status, body = _call(view, session_name="24nov10", run_number="run001", cluster_id="nope")

        assert status == 400
        assert "nope" in body["error"]

    @pytest.mark.parametrize("view", [get_metadata_summary, get_metadata_viz_data])
    def test_unknown_session(self, cluster, view):
        status, body = _call(view, session_name="ghost", run_number="run001")

        assert status == 404
        assert "ghost" in body["error"]

    def test_missing_csv_is_404(self, cluster, test_msi_session):
        with mock.patch.object(metadata_views, "fetch_remote_text", side_effect=FileNotFoundError):
            status, body = _call(get_metadata_summary, session_name="24nov10", run_number="run001")

        assert status == 404
        assert "error" in body
