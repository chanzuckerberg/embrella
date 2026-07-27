"""API tests for the deposition CRUD endpoints."""

import itertools
from unittest import mock

import pytest
from django.contrib.auth.models import User
from rest_framework.test import APIClient

DEPOSITIONS = "/depositions/v1/depositions/"
DATASETS = "/depositions/v1/datasets/"


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
