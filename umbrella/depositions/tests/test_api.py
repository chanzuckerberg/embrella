"""API tests for the deposition CRUD endpoints."""

import itertools
import json
from unittest import mock

import pytest
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

DEPOSITIONS = "/depositions/v1/depositions/"
DATASETS = "/depositions/v1/datasets/"
SESSIONS = "/depositions/v1/sessions/"


@pytest.fixture(autouse=True)
def stub_reservation():
    """Deterministic, offline id reservation (no lambda / env dependence)."""
    svc = mock.Mock()
    svc.reserve_new_deposition.side_effect = itertools.count(10001)
    svc.reserve_new_dataset.side_effect = itertools.count(20001)
    with mock.patch("depositions.views.get_reservation_service", return_value=svc):
        yield


@pytest.fixture
def user(db):
    return User.objects.create_user(username="alice@example.com", password="pw")


@pytest.fixture
def auth_client(user):
    client = APIClient()
    client.force_login(user)
    return client


def _make_deposition(client, title="Test deposition"):
    r = client.post(DEPOSITIONS, {"title": title}, format="json")
    assert r.status_code == 201, r.content
    return r.json()


def _make_dataset(client, deposition_id, title="Test dataset"):
    r = client.post(DATASETS, {"deposition": deposition_id, "title": title}, format="json")
    assert r.status_code == 201, r.content
    return r.json()


@pytest.mark.django_db
class TestAuth:
    def test_list_requires_authentication(self):
        assert APIClient().get(DEPOSITIONS, HTTP_ACCEPT="application/json").status_code == 401


@pytest.mark.django_db
class TestDepositionCrud:
    def test_create_reserves_id_and_sets_submitter(self, auth_client, user):
        body = _make_deposition(auth_client)
        assert body["deposition_id"] is not None  # reserved on create
        assert body["submitter_username"] == user.username

    def test_list_returns_envelope(self, auth_client):
        _make_deposition(auth_client)
        r = auth_client.get(DEPOSITIONS)
        assert r.status_code == 200
        data = r.json()
        assert {"submissions", "total_count"}.issubset(data)
        assert data["total_count"] == 1

    def test_patch_updates_fields(self, auth_client):
        dep = _make_deposition(auth_client)
        r = auth_client.patch(f"{DEPOSITIONS}{dep['id']}/", {"description": "updated"}, format="json")
        assert r.status_code == 200
        assert r.json()["description"] == "updated"

    def test_put_not_allowed(self, auth_client):
        dep = _make_deposition(auth_client)
        r = auth_client.put(f"{DEPOSITIONS}{dep['id']}/", {"title": "x"}, format="json")
        assert r.status_code == 405

    def test_delete(self, auth_client):
        dep = _make_deposition(auth_client)
        assert auth_client.delete(f"{DEPOSITIONS}{dep['id']}/").status_code == 204


@pytest.mark.django_db
class TestScoping:
    def test_user_can_see_anothers_deposition(self, auth_client):
        other = User.objects.create_user(username="bob@example.com", password="pw")
        other_client = APIClient()
        other_client.force_login(other)
        dep = _make_deposition(other_client)
        assert auth_client.get(f"{DEPOSITIONS}{dep['id']}/").status_code == 200

    def test_scope_mine_excludes_others(self, auth_client):
        other = User.objects.create_user(username="carol@example.com", password="pw")
        other_client = APIClient()
        other_client.force_login(other)
        others_dep = _make_deposition(other_client)
        mine = _make_deposition(auth_client)
        body = auth_client.get(f"{DEPOSITIONS}?scope=mine").json()
        ids = {s["id"] for s in body["submissions"]}
        assert mine["id"] in ids
        assert others_dep["id"] not in ids

    def test_non_owner_cannot_edit_deposition(self, auth_client):
        other = User.objects.create_user(username="dave@example.com", password="pw")
        other_client = APIClient()
        other_client.force_login(other)
        dep = _make_deposition(auth_client)  # owned by alice
        r = other_client.patch(f"{DEPOSITIONS}{dep['id']}/", {"description": "hax"}, format="json")
        assert r.status_code == 403

    def test_non_owner_cannot_delete_deposition(self, auth_client):
        other = User.objects.create_user(username="erin@example.com", password="pw")
        other_client = APIClient()
        other_client.force_login(other)
        dep = _make_deposition(auth_client)
        assert other_client.delete(f"{DEPOSITIONS}{dep['id']}/").status_code == 403

    def test_non_owner_cannot_add_dataset(self, auth_client):
        other = User.objects.create_user(username="frank@example.com", password="pw")
        other_client = APIClient()
        other_client.force_login(other)
        dep = _make_deposition(auth_client)
        r = other_client.post(DATASETS, {"deposition": dep["id"], "title": "x"}, format="json")
        assert r.status_code == 403


@pytest.mark.django_db
class TestAuthorsJsonValidation:
    def test_valid_authors_json_accepted(self, auth_client):
        dep = _make_deposition(auth_client)
        r = auth_client.patch(
            f"{DEPOSITIONS}{dep['id']}/",
            {
                "authors_json": [
                    {"author_id": 7, "author_list_order": 1, "is_primary": True, "is_corresponding": False},
                ]
            },
            format="json",
        )
        assert r.status_code == 200

    def test_free_form_snapshot_author_accepted(self, auth_client):
        dep = _make_deposition(auth_client)
        r = auth_client.patch(
            f"{DEPOSITIONS}{dep['id']}/",
            {
                "authors_json": [
                    {
                        "full_name": "Test Author",
                        "affiliation": "CZ Biohub",
                        "orcid": "0000-0002-1825-0097",
                        "is_corresponding": True,
                        "author_list_order": 0,
                    },
                ]
            },
            format="json",
        )
        assert r.status_code == 200, r.content

    def test_authors_json_wrong_field_type_rejected(self, auth_client):
        dep = _make_deposition(auth_client)
        r = auth_client.patch(
            f"{DEPOSITIONS}{dep['id']}/",
            {"authors_json": [{"author_id": "seven"}]},
            format="json",
        )
        assert r.status_code == 400
        assert "authors_json" in r.json()

    def test_authors_json_not_a_list_rejected(self, auth_client):
        dep = _make_deposition(auth_client)
        r = auth_client.patch(f"{DEPOSITIONS}{dep['id']}/", {"authors_json": "nope"}, format="json")
        assert r.status_code == 400


@pytest.mark.django_db
class TestDatasetFundingSync:
    def test_add_funding(self, auth_client):
        dep = _make_deposition(auth_client)
        ds = _make_dataset(auth_client, dep["id"])
        r = auth_client.patch(
            f"{DATASETS}{ds['id']}/",
            {"funding": [{"funding_agency_name": "NIH", "grant_id": "G1"}]},
            format="json",
        )
        assert r.status_code == 200
        funding = r.json()["funding"]
        assert len(funding) == 1
        assert funding[0]["funding_agency_name"] == "NIH"

    def test_funding_replace_deletes_missing(self, auth_client):
        dep = _make_deposition(auth_client)
        ds = _make_dataset(auth_client, dep["id"])
        r = auth_client.patch(
            f"{DATASETS}{ds['id']}/",
            {"funding": [{"funding_agency_name": "NIH"}, {"funding_agency_name": "NSF"}]},
            format="json",
        )
        keep_id = r.json()["funding"][0]["id"]

        r = auth_client.patch(
            f"{DATASETS}{ds['id']}/",
            {"funding": [{"id": keep_id, "funding_agency_name": "NIH-renamed"}]},
            format="json",
        )
        funding = r.json()["funding"]
        assert len(funding) == 1
        assert funding[0]["funding_agency_name"] == "NIH-renamed"

    def test_stray_funding_id_does_not_500(self, auth_client):
        """A funding id that isn't this dataset's must create a fresh row, not crash."""
        dep = _make_deposition(auth_client)
        ds = _make_dataset(auth_client, dep["id"])
        r = auth_client.patch(
            f"{DATASETS}{ds['id']}/",
            {"funding": [{"id": 999999, "funding_agency_name": "Ghost"}]},
            format="json",
        )
        assert r.status_code == 200
        assert len(r.json()["funding"]) == 1


@pytest.mark.django_db
class TestDatasetSessionGuard:
    def test_session_without_msi_session_returns_400(self, auth_client):
        """Missing msi_session must be a clean 400, not a 500 KeyError."""
        dep = _make_deposition(auth_client)
        ds = _make_dataset(auth_client, dep["id"])
        r = auth_client.patch(
            f"{DATASETS}{ds['id']}/",
            {"sessions": [{"aretomo_run_name": "run1"}]},
            format="json",
        )
        assert r.status_code == 400
        assert "sessions" in r.json()


@pytest.fixture
def owned_session(user):
    """A DepositionSession under a deposition owned by `user` (the auth_client user)."""
    from tem.models import Camera, ImagingWorkflow, Microscope, MsiSession, SessionPlan, Software

    from depositions.models import Dataset, Deposition, DepositionSession

    dep = Deposition.objects.create(submitter_user=user, title="Dep")
    ds = Dataset.objects.create(deposition=dep, title="DS")
    session_plan = SessionPlan.objects.create(
        scope=Microscope.objects.create(name="TestScope", cs=2.7),
        camera=Camera.objects.create(name="TestCamera", root_dir="/r", frame_format="eer", initial_frame_base_dir="/f"),
        imaging_workflow=ImagingWorkflow.objects.create(imaging_mode="tem", workflow="tomo"),
        software=Software.objects.create(name="SW"),
    )
    msi = MsiSession.objects.create(name="24nov10", session_plan=session_plan)
    return DepositionSession.objects.create(dataset=ds, msi_session=msi)


@pytest.mark.django_db
class TestSubsetUpload:
    """POST /sessions/<id>/subset-csv/ parses + stores the selection in the DB."""

    def _url(self, session):
        return f"{SESSIONS}{session.id}/subset-csv/"

    def test_upload_json_stores_selection_and_clears_path(self, auth_client, owned_session):
        owned_session.subset_csv_path = "/old/path.csv"
        owned_session.save(update_fields=["subset_csv_path"])
        payload = {"Selected positions": ["Position_1", "Position_2"], "Filter type": "AND"}
        upload = SimpleUploadedFile("Metadata.json", json.dumps(payload).encode(), content_type="application/json")
        r = auth_client.post(self._url(owned_session), {"file": upload}, format="multipart")
        assert r.status_code == 200, r.content
        assert r.json()["subset_selection"] == payload
        assert r.json()["subset_filename"] == "Metadata.json"
        owned_session.refresh_from_db()
        assert owned_session.subset_selection == payload
        assert owned_session.subset_filename == "Metadata.json"
        assert owned_session.subset_csv_path == ""  # upload clears any cluster path

    def test_missing_file_returns_400(self, auth_client, owned_session):
        r = auth_client.post(self._url(owned_session), {}, format="multipart")
        assert r.status_code == 400

    def test_unsupported_extension_returns_400(self, auth_client, owned_session):
        upload = SimpleUploadedFile("subset.txt", b"nope", content_type="text/plain")
        r = auth_client.post(self._url(owned_session), {"file": upload}, format="multipart")
        assert r.status_code == 400

    def test_malformed_json_returns_400(self, auth_client, owned_session):
        upload = SimpleUploadedFile("Metadata.json", b"{not json", content_type="application/json")
        r = auth_client.post(self._url(owned_session), {"file": upload}, format="multipart")
        assert r.status_code == 400

    def test_non_owner_cannot_upload(self, owned_session):
        other = User.objects.create_user(username="grace@example.com", password="pw")
        client = APIClient()
        client.force_login(other)
        upload = SimpleUploadedFile("Metadata.json", b"{}", content_type="application/json")
        r = client.post(f"{SESSIONS}{owned_session.id}/subset-csv/", {"file": upload}, format="multipart")
        assert r.status_code == 403


@pytest.mark.django_db
class TestAutoFill:
    """POST /sessions/<id>/auto-fill/ runs cryoetportalprep init and populates metadata."""

    def _url(self, session):
        return f"{SESSIONS}{session.id}/auto-fill/"

    def _patch_cluster(self):
        """Isolate the SSH/path plumbing so tests exercise the view, not the cluster."""
        return (
            mock.patch("depositions.views.cluster_id_for_run", return_value="bruno"),
            mock.patch("depositions.views.Cluster"),
            mock.patch("depositions.views.resolve_review_path", return_value="/hpc/aretomo3/24nov10/run001"),
        )

    def test_requires_an_aretomo_run(self, auth_client, owned_session):
        # owned_session has a blank aretomo_run_name
        r = auth_client.post(self._url(owned_session))
        assert r.status_code == 400

    def test_populates_metadata_and_stamps(self, auth_client, owned_session):
        from depositions.models import TiltseriesMetadata, TomogramMetadata

        owned_session.aretomo_run_name = "run001"
        owned_session.save(update_fields=["aretomo_run_name"])

        raw = {
            "total_dose": 120.0,
            "tilt_axis_angle": None,
            "acquisition": {
                "pixel_spacing": 1.54,
                "acceleration_voltage_kv": 300.0,
                "spherical_aberration_constant": 2.7,
                "aretomo_version": "AreTomo3 2.1.0",
                "binned_voxel_ratio": 8,
            },
        }
        c1, c2, c3 = self._patch_cluster()
        with (
            c1,
            c2,
            c3,
            mock.patch(
                "depositions.views.run_autofill_init",
                return_value={"filled": True, "session": raw, "reason": None},
            ),
        ):
            r = auth_client.post(self._url(owned_session))

        assert r.status_code == 200, r.content
        ts = TiltseriesMetadata.objects.get(session=owned_session)
        assert ts.pixel_spacing == 1.54
        assert ts.acceleration_voltage == 300.0
        assert ts.total_flux == 120.0
        assert ts.tilt_axis is None
        assert ts.autofill_metadata == raw
        tomos = {t.flavor: t for t in TomogramMetadata.objects.filter(session=owned_session)}
        assert set(tomos) == {"denoised", "filtered"}
        assert tomos["denoised"].reconstruction_software == "AreTomo3 2.1.0"
        assert tomos["denoised"].voxel_spacing == 12.32
        assert tomos["denoised"].processing_software == "DenoisET"
        assert tomos["denoised"].is_visualization_default is True
        assert tomos["filtered"].processing_software == "AreTomo3 2.1.0"
        assert tomos["filtered"].is_visualization_default is False
        assert tomos["denoised"].autofill_metadata == raw
        owned_session.refresh_from_db()
        assert owned_session.last_autofill_at is not None
        assert owned_session.last_autofill_duration_seconds is not None

    def test_prunes_stale_flavor_rows(self, auth_client, owned_session):
        """Re-running auto-fill drops a leftover pre-migration flavor="" row."""
        from depositions.models import TomogramMetadata

        owned_session.aretomo_run_name = "run001"
        owned_session.save(update_fields=["aretomo_run_name"])
        TomogramMetadata.objects.create(session=owned_session, flavor="", reconstruction_software="old")

        raw = {"acquisition": {"aretomo_version": "AreTomo3 2.1.0", "pixel_spacing": 1.5, "binned_voxel_ratio": 8}}
        c1, c2, c3 = self._patch_cluster()
        with (
            c1,
            c2,
            c3,
            mock.patch(
                "depositions.views.run_autofill_init",
                return_value={"filled": True, "session": raw, "reason": None},
            ),
        ):
            r = auth_client.post(self._url(owned_session))

        assert r.status_code == 200, r.content
        flavors = {t.flavor for t in TomogramMetadata.objects.filter(session=owned_session)}
        assert flavors == {"denoised", "filtered"}  # stale "" row pruned

    def test_unprefixed_run_is_normalized_to_run_dir(self, auth_client, owned_session):
        # Runs are stored as "001" but the cluster dir is "run001" - the view must prefix it.
        owned_session.aretomo_run_name = "001"
        owned_session.save(update_fields=["aretomo_run_name"])
        resolve = mock.patch("depositions.views.resolve_review_path", return_value="/hpc/aretomo3/x/run001")
        with (
            mock.patch("depositions.views.cluster_id_for_run", return_value="bruno"),
            mock.patch("depositions.views.Cluster"),
            resolve as resolve_mock,
            mock.patch(
                "depositions.views.run_autofill_init",
                return_value={"filled": True, "session": {"acquisition": {}}, "reason": None},
            ),
        ):
            r = auth_client.post(self._url(owned_session))
        assert r.status_code == 200, r.content
        assert resolve_mock.call_args.kwargs["run"] == "run001"

    def test_init_failure_returns_502(self, auth_client, owned_session):
        owned_session.aretomo_run_name = "run001"
        owned_session.save(update_fields=["aretomo_run_name"])
        c1, c2, c3 = self._patch_cluster()
        with (
            c1,
            c2,
            c3,
            mock.patch(
                "depositions.views.run_autofill_init",
                return_value={"filled": False, "session": None, "reason": "Metrics file not found"},
            ),
        ):
            r = auth_client.post(self._url(owned_session))
        assert r.status_code == 502
        detail = r.json()["detail"]
        assert "Metrics file not found" not in detail
        assert "AreTomo run" in detail

    def test_non_owner_cannot_autofill(self, owned_session):
        other = User.objects.create_user(username="heidi@example.com", password="pw")
        client = APIClient()
        client.force_login(other)
        r = client.post(f"{SESSIONS}{owned_session.id}/auto-fill/")
        assert r.status_code == 403


@pytest.mark.django_db
class TestTomogramFlavorValidation:
    """PATCH /sessions/<id> tomogram_metadata must carry valid, unique flavors."""

    def _patch(self, auth_client, session, tomos):
        return auth_client.patch(f"{SESSIONS}{session.id}/", {"tomogram_metadata": tomos}, format="json")

    def test_accepts_denoised_and_filtered(self, auth_client, owned_session):
        from depositions.models import TomogramMetadata

        r = self._patch(
            auth_client,
            owned_session,
            [{"flavor": "denoised", "voxel_spacing": 7.84}, {"flavor": "filtered", "voxel_spacing": 7.84}],
        )
        assert r.status_code == 200, r.content
        assert {t.flavor for t in TomogramMetadata.objects.filter(session=owned_session)} == {"denoised", "filtered"}

    def test_rejects_invalid_flavor(self, auth_client, owned_session):
        r = self._patch(auth_client, owned_session, [{"flavor": "raw", "voxel_spacing": 7.84}])
        assert r.status_code == 400

    def test_rejects_blank_flavor(self, auth_client, owned_session):
        r = self._patch(auth_client, owned_session, [{"flavor": "", "voxel_spacing": 7.84}])
        assert r.status_code == 400

    def test_rejects_missing_flavor(self, auth_client, owned_session):
        r = self._patch(auth_client, owned_session, [{"voxel_spacing": 7.84}])
        assert r.status_code == 400

    def test_rejects_duplicate_flavor(self, auth_client, owned_session):
        r = self._patch(auth_client, owned_session, [{"flavor": "denoised"}, {"flavor": "denoised"}])
        assert r.status_code == 400


@pytest.mark.django_db
class TestDatasetLoadsSessionMetadata:
    """Dataset GET must return saved session metadata so the wizard reloads edits on reopen"""

    def test_dataset_get_includes_saved_metadata(self, auth_client, owned_session):
        from depositions.models import TiltseriesMetadata, TomogramMetadata

        TiltseriesMetadata.objects.create(session=owned_session, acceleration_voltage=302)
        TomogramMetadata.objects.create(session=owned_session, flavor="denoised", voxel_spacing=7.84)

        r = auth_client.get(f"{DATASETS}{owned_session.dataset_id}/")
        assert r.status_code == 200, r.content
        sess = next(s for s in r.json()["sessions"] if s["id"] == owned_session.id)
        assert sess["tiltseries_metadata"]["acceleration_voltage"] == 302
        assert sess["tomogram_metadata"][0]["flavor"] == "denoised"
        assert sess["tomogram_metadata"][0]["voxel_spacing"] == 7.84

    def test_dataset_get_without_metadata_does_not_error(self, auth_client, owned_session):
        r = auth_client.get(f"{DATASETS}{owned_session.dataset_id}/")
        assert r.status_code == 200, r.content
        sess = next(s for s in r.json()["sessions"] if s["id"] == owned_session.id)
        assert sess.get("tiltseries_metadata") is None
        assert sess["tomogram_metadata"] == []
