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

    def test_populates_instrument_from_tem(self, auth_client, owned_session):
        """Facility-record fields come from the session's Microscope/Camera."""
        from depositions.models import TiltseriesMetadata

        plan = owned_session.msi_session.session_plan
        plan.scope.manufacturer = "TFS"
        plan.scope.model = "Krios G4"
        plan.scope.energy_filter = "Selectris X"
        plan.scope.phase_plate = "Volta"
        plan.scope.image_correctors = ["Cs corrector"]
        plan.scope.save()
        plan.camera.manufacturer = "Gatan"
        plan.camera.model = "K3"
        plan.camera.save()

        owned_session.aretomo_run_name = "run001"
        owned_session.save(update_fields=["aretomo_run_name"])

        c1, c2, c3 = self._patch_cluster()
        with (
            c1,
            c2,
            c3,
            mock.patch(
                "depositions.views.run_autofill_init",
                return_value={"filled": True, "session": {"acquisition": {}}, "reason": None},
            ),
        ):
            r = auth_client.post(self._url(owned_session))

        assert r.status_code == 200, r.content
        ts = TiltseriesMetadata.objects.get(session=owned_session)
        assert ts.microscope_manufacturer == "TFS"
        assert ts.microscope_model == "Krios G4"
        assert ts.microscope_energy_filter == "Selectris X"
        assert ts.microscope_phase_plate == "Volta"
        assert ts.microscope_image_corrector == "Cs corrector"
        assert ts.camera_manufacturer == "Gatan"
        assert ts.camera_model == "K3"

    def test_rerun_with_blank_tem_keeps_manual_instrument_edits(self, auth_client, owned_session):
        """A second auto-fill must not wipe instrument fields the user typed while the tem row is blank."""
        from depositions.models import TiltseriesMetadata

        # tem scope/camera are blank (defaults); the user typed a phase_plate by hand.
        TiltseriesMetadata.objects.create(session=owned_session, microscope_phase_plate="Volta (manual)")
        owned_session.aretomo_run_name = "run001"
        owned_session.save(update_fields=["aretomo_run_name"])

        c1, c2, c3 = self._patch_cluster()
        with (
            c1,
            c2,
            c3,
            mock.patch(
                "depositions.views.run_autofill_init",
                return_value={"filled": True, "session": {"acquisition": {}}, "reason": None},
            ),
        ):
            r = auth_client.post(self._url(owned_session))

        assert r.status_code == 200, r.content
        ts = TiltseriesMetadata.objects.get(session=owned_session)
        assert ts.microscope_phase_plate == "Volta (manual)"  # blank tem didn't overwrite the edit

    def test_populated_tem_overwrites_existing_value(self, auth_client, owned_session):
        """The other half of the contract: a populated tem value wins over an existing row value."""
        from depositions.models import TiltseriesMetadata

        TiltseriesMetadata.objects.create(session=owned_session, microscope_manufacturer="OldCorp")
        plan = owned_session.msi_session.session_plan
        plan.scope.manufacturer = "TFS"
        plan.scope.save()
        owned_session.aretomo_run_name = "run001"
        owned_session.save(update_fields=["aretomo_run_name"])

        c1, c2, c3 = self._patch_cluster()
        with (
            c1,
            c2,
            c3,
            mock.patch(
                "depositions.views.run_autofill_init",
                return_value={"filled": True, "session": {"acquisition": {}}, "reason": None},
            ),
        ):
            r = auth_client.post(self._url(owned_session))

        assert r.status_code == 200, r.content
        ts = TiltseriesMetadata.objects.get(session=owned_session)
        assert ts.microscope_manufacturer == "TFS"  # tem value overwrote the old one

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
        assert ts.data_acquisition_software == "SW"
        assert ts.autofill_metadata == raw
        assert ts.is_aligned is False
        assert ts.aligned_tiltseries_binning == 1
        assert ts.binning_from_frames is None
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

    def _run_autofill(self, auth_client, session, raw):
        c1, c2, c3 = self._patch_cluster()
        with (
            c1,
            c2,
            c3,
            mock.patch("depositions.views.run_autofill_init", return_value={"filled": True, "session": raw, "reason": None}),
        ):
            return auth_client.post(self._url(session))

    def test_rerun_preserves_manual_binning_that_differs_from_volume_binning(self, auth_client, owned_session):
        """binning_from_frames is manual; the mapper never sets it, so a re-run keeps the stored value."""
        from depositions.models import TiltseriesMetadata

        owned_session.aretomo_run_name = "run001"
        owned_session.save(update_fields=["aretomo_run_name"])
        TiltseriesMetadata.objects.create(session=owned_session, binning_from_frames=2)

        r = self._run_autofill(auth_client, owned_session, {"acquisition": {"binned_voxel_ratio": 8}})

        assert r.status_code == 200, r.content
        assert TiltseriesMetadata.objects.get(session=owned_session).binning_from_frames == 2

    def test_rerun_preserves_manual_binning_that_matches_volume_binning(self, auth_client, owned_session):
        """A deliberate value equal to volume binning must survive — equality does not prove it was auto-set."""
        from depositions.models import TiltseriesMetadata

        owned_session.aretomo_run_name = "run001"
        owned_session.save(update_fields=["aretomo_run_name"])
        TiltseriesMetadata.objects.create(session=owned_session, binning_from_frames=8)

        r = self._run_autofill(auth_client, owned_session, {"acquisition": {"binned_voxel_ratio": 8}})

        assert r.status_code == 200, r.content
        assert TiltseriesMetadata.objects.get(session=owned_session).binning_from_frames == 8

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
        assert resolve_mock.call_args.kwargs["proc_run"] == "run001"

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
class TestManualSaveStampsAlignment:
    def _patch(self, auth_client, session, tiltseries):
        return auth_client.patch(f"{SESSIONS}{session.id}/", {"tiltseries_metadata": tiltseries}, format="json")

    def test_manual_tiltseries_save_sets_alignment_values(self, auth_client, owned_session):
        from depositions.models import TiltseriesMetadata

        r = self._patch(auth_client, owned_session, {"acceleration_voltage": 300, "pixel_spacing": 1.54})
        assert r.status_code == 200, r.content
        ts = TiltseriesMetadata.objects.get(session=owned_session)
        assert ts.is_aligned is False
        assert ts.aligned_tiltseries_binning == 1

    def test_fixed_pair_wins_over_any_client_supplied_values(self, auth_client, owned_session):
        from depositions.models import TiltseriesMetadata

        r = self._patch(auth_client, owned_session, {"is_aligned": True, "aligned_tiltseries_binning": 4})
        assert r.status_code == 200, r.content
        ts = TiltseriesMetadata.objects.get(session=owned_session)
        assert ts.is_aligned is False
        assert ts.aligned_tiltseries_binning == 1


@pytest.mark.django_db
class TestDatasetLoadsSessionMetadata:
    """Dataset GET must return saved session metadata so the wizard reloads edits on reopen"""

    def test_dataset_get_includes_saved_metadata(self, auth_client, owned_session):
        from django.utils import timezone

        from depositions.models import TiltseriesMetadata, TomogramMetadata

        TiltseriesMetadata.objects.create(session=owned_session, acceleration_voltage=302)
        TomogramMetadata.objects.create(session=owned_session, flavor="denoised", voxel_spacing=7.84)
        owned_session.last_autofill_at = timezone.now()
        owned_session.save(update_fields=["last_autofill_at"])

        r = auth_client.get(f"{DATASETS}{owned_session.dataset_id}/")
        assert r.status_code == 200, r.content
        sess = next(s for s in r.json()["sessions"] if s["id"] == owned_session.id)
        assert sess["tiltseries_metadata"]["acceleration_voltage"] == 302
        assert sess["tomogram_metadata"][0]["flavor"] == "denoised"
        assert sess["tomogram_metadata"][0]["voxel_spacing"] == 7.84
        # last_autofill_at must load too, else the wizard shows "Auto-fill" (not "Re-run") on reopen
        # and skips the overwrite confirm.
        assert sess["last_autofill_at"] is not None

    def test_dataset_get_without_metadata_does_not_error(self, auth_client, owned_session):
        r = auth_client.get(f"{DATASETS}{owned_session.dataset_id}/")
        assert r.status_code == 200, r.content
        sess = next(s for s in r.json()["sessions"] if s["id"] == owned_session.id)
        assert sess.get("tiltseries_metadata") is None
        assert sess["tomogram_metadata"] == []


@pytest.mark.django_db
class TestAnnotationPersistence:
    """PATCH /sessions/<id>/ upserts annotations by (copick_kind, copick_ref) with full-replace."""

    def _url(self, session):
        return f"{SESSIONS}{session.id}/"

    def _ann(self, ref, **over):
        return {"copick_kind": "picks", "copick_ref": ref, "object_name": "ribosome", **over}

    def _patch(self, client, session, annotations):
        return client.patch(self._url(session), {"annotations": annotations}, format="json")

    def test_creates_annotations(self, auth_client, owned_session):
        from depositions.models import DepositionAnnotation

        r = self._patch(
            auth_client, owned_session, [self._ann("ribosome-0"), self._ann("mito-0", copick_kind="segmentations")]
        )
        assert r.status_code == 200, r.content
        assert DepositionAnnotation.objects.filter(session=owned_session).count() == 2

    def test_upserts_by_kind_and_ref(self, auth_client, owned_session):
        from depositions.models import DepositionAnnotation

        self._patch(auth_client, owned_session, [self._ann("ribosome-0", object_count=100)])
        r = self._patch(auth_client, owned_session, [self._ann("ribosome-0", object_count=250)])
        assert r.status_code == 200, r.content
        qs = DepositionAnnotation.objects.filter(session=owned_session)
        assert qs.count() == 1
        assert qs.first().object_count == 250

    def test_full_replace_drops_omitted(self, auth_client, owned_session):
        from depositions.models import DepositionAnnotation

        self._patch(auth_client, owned_session, [self._ann("a"), self._ann("b")])
        r = self._patch(auth_client, owned_session, [self._ann("a")])
        assert r.status_code == 200, r.content
        refs = set(DepositionAnnotation.objects.filter(session=owned_session).values_list("copick_ref", flat=True))
        assert refs == {"a"}

    def test_empty_list_clears_all(self, auth_client, owned_session):
        from depositions.models import DepositionAnnotation

        self._patch(auth_client, owned_session, [self._ann("a")])
        r = self._patch(auth_client, owned_session, [])
        assert r.status_code == 200, r.content
        assert DepositionAnnotation.objects.filter(session=owned_session).count() == 0

    def test_omitting_annotations_key_leaves_them_untouched(self, auth_client, owned_session):
        from depositions.models import DepositionAnnotation

        self._patch(auth_client, owned_session, [self._ann("a")])
        r = auth_client.patch(self._url(owned_session), {"tiltseries_metadata": {"pixel_spacing": 1.5}}, format="json")
        assert r.status_code == 200, r.content
        assert DepositionAnnotation.objects.filter(session=owned_session).count() == 1

    def test_get_returns_annotations(self, auth_client, owned_session):
        self._patch(auth_client, owned_session, [self._ann("a")])
        r = auth_client.get(self._url(owned_session))
        assert r.status_code == 200
        assert [a["copick_ref"] for a in r.json()["annotations"]] == ["a"]

    def test_non_owner_cannot_patch(self, owned_session):
        other = User.objects.create_user(username="mallory@example.com", password="pw")
        client = APIClient()
        client.force_login(other)
        r = self._patch(client, owned_session, [self._ann("a")])
        assert r.status_code == 403

    def test_creates_nested_method_links(self, auth_client, owned_session):
        from depositions.models import DepositionAnnotation

        links = [
            {"link_type": "source_code", "link": "https://github.com/x/y"},
            {"link_type": "website", "link": "https://example.org", "custom_name": "Project"},
        ]
        r = self._patch(auth_client, owned_session, [self._ann("a", method_links=links)])
        assert r.status_code == 200, r.content
        ann = DepositionAnnotation.objects.get(session=owned_session, copick_ref="a")
        assert ann.method_links.count() == 2
        assert set(ann.method_links.values_list("link_type", flat=True)) == {"source_code", "website"}

    def test_upserts_and_drops_method_links_by_id(self, auth_client, owned_session):
        from depositions.models import DepositionAnnotation

        r = self._patch(
            auth_client,
            owned_session,
            [self._ann("a", method_links=[{"link_type": "website", "link": "https://a.org"}])],
        )
        link = DepositionAnnotation.objects.get(session=owned_session, copick_ref="a").method_links.get()
        # Re-patch with the id present (edit) - should update in place, not duplicate.
        r = self._patch(
            auth_client,
            owned_session,
            [self._ann("a", method_links=[{"id": link.id, "link_type": "website", "link": "https://b.org"}])],
        )
        assert r.status_code == 200, r.content
        ann = DepositionAnnotation.objects.get(session=owned_session, copick_ref="a")
        assert ann.method_links.count() == 1
        assert ann.method_links.get().link == "https://b.org"
        # Re-patch with an empty list - should drop the link.
        self._patch(auth_client, owned_session, [self._ann("a", method_links=[])])
        assert ann.method_links.count() == 0

    def test_stale_link_id_creates_new_row_not_integrity_error(self, auth_client, owned_session):
        from depositions.models import DepositionAnnotation

        # An id that doesn't belong to this annotation must NOT crash - it's treated as a new row.
        r = self._patch(
            auth_client,
            owned_session,
            [self._ann("a", method_links=[{"id": 999999, "link_type": "website", "link": "https://a.org"}])],
        )
        assert r.status_code == 200, r.content
        ann = DepositionAnnotation.objects.get(session=owned_session, copick_ref="a")
        assert ann.method_links.count() == 1
        assert ann.method_links.get().id != 999999

    def test_get_returns_nested_method_links(self, auth_client, owned_session):
        self._patch(
            auth_client,
            owned_session,
            [self._ann("a", method_links=[{"link_type": "website", "link": "https://a.org"}])],
        )
        r = auth_client.get(self._url(owned_session))
        assert r.status_code == 200
        links = r.json()["annotations"][0]["method_links"]
        assert links[0]["link"] == "https://a.org"
        assert "id" in links[0]

    def test_dataset_payload_reloads_annotations_with_method_links(self, auth_client, owned_session):
        """The wizard seeds from GET /datasets/<id> — its nested sessions must carry annotations back."""
        self._patch(
            auth_client,
            owned_session,
            [self._ann("a", object_id="GO:1", method_links=[{"link_type": "website", "link": "https://a.org"}])],
        )
        r = auth_client.get(f"{DATASETS}{owned_session.dataset_id}/")
        assert r.status_code == 200, r.content
        session = r.json()["sessions"][0]
        assert [a["copick_ref"] for a in session["annotations"]] == ["a"]
        assert session["annotations"][0]["object_id"] == "GO:1"
        assert session["annotations"][0]["method_links"][0]["link"] == "https://a.org"

    def test_dataset_payload_annotations_do_not_n_plus_1(self, auth_client, owned_session):
        """GET /datasets/<id> query count must not grow with annotation count."""
        from django.db import connection
        from django.test.utils import CaptureQueriesContext

        url = f"{DATASETS}{owned_session.dataset_id}/"
        links = [{"link_type": "website", "link": f"https://l{i}.org"} for i in range(3)]

        self._patch(auth_client, owned_session, [self._ann(f"a{i}", method_links=links) for i in range(2)])
        with CaptureQueriesContext(connection) as few:
            assert auth_client.get(url).status_code == 200

        self._patch(auth_client, owned_session, [self._ann(f"a{i}", method_links=links) for i in range(20)])
        with CaptureQueriesContext(connection) as many:
            r = auth_client.get(url)
        assert r.status_code == 200, r.content
        anns = r.json()["sessions"][0]["annotations"]
        assert len(anns) == 20
        assert len(anns[0]["method_links"]) == 3  # else a flat count would pass with the link nesting gone
        assert len(many) == len(few), f"query count grew with annotation count: {len(few)} -> {len(many)}"

    def test_deposition_payload_annotations_do_not_n_plus_1(self, auth_client, owned_session):
        """GET /depositions/<id> nests the same annotations -> method_links; query count must stay flat."""
        from django.db import connection
        from django.test.utils import CaptureQueriesContext

        url = f"{DEPOSITIONS}{owned_session.dataset.deposition_id}/"
        links = [{"link_type": "website", "link": f"https://l{i}.org"} for i in range(3)]

        self._patch(auth_client, owned_session, [self._ann(f"a{i}", method_links=links) for i in range(2)])
        with CaptureQueriesContext(connection) as few:
            assert auth_client.get(url).status_code == 200

        self._patch(auth_client, owned_session, [self._ann(f"a{i}", method_links=links) for i in range(20)])
        with CaptureQueriesContext(connection) as many:
            r = auth_client.get(url)
        assert r.status_code == 200
        # Check the links are actually there, so a flat query count can't pass with the nesting gone.
        anns = r.json()["datasets"][0]["sessions"][0]["annotations"]
        assert len(anns) == 20
        assert len(anns[0]["method_links"]) == 3
        assert len(many) == len(few), f"query count grew with annotation count: {len(few)} -> {len(many)}"

    def test_patch_response_reflects_written_links(self, auth_client, owned_session):
        """The PATCH body itself must serialize freshly-written annotations + links (not a stale prefetch)."""
        r = self._patch(
            auth_client,
            owned_session,
            [self._ann("a", method_links=[{"link_type": "website", "link": "https://fresh.org"}])],
        )
        assert r.status_code == 200, r.content
        anns = r.json()["annotations"]
        assert [a["copick_ref"] for a in anns] == ["a"]
        link = anns[0]["method_links"][0]
        assert link["link"] == "https://fresh.org"
        assert isinstance(link.get("id"), int)


@pytest.mark.django_db
class TestSelectedCopickRunsShape:
    """selected_copick_runs must be a list of unique, non-empty run-name strings."""

    def _url(self, session):
        return f"{SESSIONS}{session.id}/"

    def _patch(self, client, session, runs):
        return client.patch(self._url(session), {"selected_copick_runs": runs}, format="json")

    def test_accepts_list_of_run_names(self, auth_client, owned_session):
        r = self._patch(auth_client, owned_session, ["run001", "run003"])
        assert r.status_code == 200, r.content
        owned_session.refresh_from_db()
        assert owned_session.selected_copick_runs == ["run001", "run003"]

    def test_accepts_empty_list(self, auth_client, owned_session):
        r = self._patch(auth_client, owned_session, [])
        assert r.status_code == 200, r.content

    def test_rejects_non_list(self, auth_client, owned_session):
        r = self._patch(auth_client, owned_session, "run001")
        assert r.status_code == 400
        assert "selected_copick_runs" in r.json()

    def test_rejects_non_string_entry(self, auth_client, owned_session):
        r = self._patch(auth_client, owned_session, ["run001", 123])
        assert r.status_code == 400

    def test_rejects_empty_string_entry(self, auth_client, owned_session):
        r = self._patch(auth_client, owned_session, ["run001", "  "])
        assert r.status_code == 400

    def test_rejects_duplicates(self, auth_client, owned_session):
        r = self._patch(auth_client, owned_session, ["run001", "run001"])
        assert r.status_code == 400

    def test_dataset_nested_session_also_validates(self, auth_client, owned_session):
        r = auth_client.patch(
            f"{DATASETS}{owned_session.dataset_id}/",
            {"sessions": [{"msi_session": owned_session.msi_session_id, "selected_copick_runs": [123]}]},
            format="json",
        )
        assert r.status_code == 400
