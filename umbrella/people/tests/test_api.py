"""DRF CRUD API tests for the people directory endpoints."""

import pytest
from django.contrib.auth.models import User
from rest_framework.test import APIClient

from people.models import Institution, Person


@pytest.fixture
def user(db):
    return User.objects.create_user(username="test@example.com", password="pw")


@pytest.fixture
def auth_client(user):
    client = APIClient()
    client.force_login(user)
    return client


@pytest.mark.django_db
class TestAuthRequired:
    def test_list_requires_authentication(self):
        client = APIClient()
        assert client.get("/people/v1/people/", HTTP_ACCEPT="application/json").status_code == 401

    def test_institutions_require_authentication(self):
        client = APIClient()
        assert client.get("/people/v1/institutions/", HTTP_ACCEPT="application/json").status_code == 401


@pytest.mark.django_db
class TestPersonCrud:
    def test_create_person(self, auth_client):
        response = auth_client.post(
            "/people/v1/people/",
            data={
                "given_name": "Test",
                "family_name": "User",
                "orcid": "0000-0002-1825-0097",
                "contact_email": "test@example.com",
            },
            format="json",
        )
        assert response.status_code == 201, response.content
        assert Person.objects.filter(orcid="0000-0002-1825-0097").exists()

    def test_create_person_blank_orcid_stored_as_null(self, auth_client):
        response = auth_client.post(
            "/people/v1/people/",
            data={"given_name": "Alan", "family_name": "Turing", "orcid": ""},
            format="json",
        )
        assert response.status_code == 201, response.content
        person = Person.objects.get(id=response.json()["id"])
        assert person.orcid is None

    def test_create_person_invalid_orcid_rejected(self, auth_client):
        response = auth_client.post(
            "/people/v1/people/",
            data={"given_name": "Bad", "family_name": "Orcid", "orcid": "not-an-orcid"},
            format="json",
        )
        assert response.status_code == 400
        assert "orcid" in response.json()

    def test_duplicate_orcid_returns_400(self, auth_client):
        Person.objects.create(given_name="Ada", family_name="Lovelace", orcid="0000-0002-1825-0097")
        response = auth_client.post(
            "/people/v1/people/",
            data={"given_name": "Grace", "family_name": "Hopper", "orcid": "0000-0002-1825-0097"},
            format="json",
        )
        assert response.status_code == 400
        assert "orcid" in response.json()

    def test_retrieve_person_includes_institution(self, auth_client):
        inst = Institution.objects.create(name="Biohub")
        person = Person.objects.create(given_name="Ada", family_name="Lovelace", institution=inst)

        response = auth_client.get(f"/people/v1/people/{person.id}/")
        assert response.status_code == 200
        data = response.json()
        # the full institution object is nested inline
        assert data["institution"]["id"] == inst.id
        assert data["institution"]["name"] == "Biohub"
        assert data["institution"]["ror_id"] == ""

    def test_create_person_with_institution(self, auth_client):
        inst = Institution.objects.create(name="Biohub")
        response = auth_client.post(
            "/people/v1/people/",
            data={"given_name": "Ada", "family_name": "Lovelace", "institution_id": inst.id},
            format="json",
        )
        assert response.status_code == 201, response.content
        body = response.json()
        assert Person.objects.get(id=body["id"]).institution_id == inst.id
        # response echoes the full nested institution, not just the id
        assert body["institution"]["name"] == "Biohub"

    def test_patch_person(self, auth_client):
        person = Person.objects.create(given_name="Ada", family_name="Lovelace")
        response = auth_client.patch(
            f"/people/v1/people/{person.id}/",
            data={"contact_email": "ada@new.example.com"},
            format="json",
        )
        assert response.status_code == 200
        person.refresh_from_db()
        assert person.contact_email == "ada@new.example.com"

    def test_delete_person(self, auth_client):
        person = Person.objects.create(given_name="Ada", family_name="Lovelace")
        response = auth_client.delete(f"/people/v1/people/{person.id}/")
        assert response.status_code == 204
        assert not Person.objects.filter(id=person.id).exists()

    def test_search_by_family_name(self, auth_client):
        Person.objects.create(given_name="Ada", family_name="Lovelace")
        Person.objects.create(given_name="Alan", family_name="Turing")

        response = auth_client.get("/people/v1/people/?search=Lovelace")
        assert response.status_code == 200
        results = response.json()["results"]
        assert len(results) == 1
        assert results[0]["family_name"] == "Lovelace"


@pytest.mark.django_db
class TestPersonByIds:
    def test_fetch_comma_separated(self, auth_client):
        ada = Person.objects.create(given_name="Ada", family_name="Lovelace")
        alan = Person.objects.create(given_name="Alan", family_name="Turing")
        Person.objects.create(given_name="Grace", family_name="Hopper")

        response = auth_client.get(f"/people/v1/people/by-ids/?ids={ada.id},{alan.id}")
        assert response.status_code == 200
        data = response.json()
        assert {p["id"] for p in data} == {ada.id, alan.id}

    def test_fetch_repeated_param(self, auth_client):
        ada = Person.objects.create(given_name="Ada", family_name="Lovelace")
        alan = Person.objects.create(given_name="Alan", family_name="Turing")

        response = auth_client.get(f"/people/v1/people/by-ids/?ids={ada.id}&ids={alan.id}")
        assert response.status_code == 200
        assert {p["id"] for p in response.json()} == {ada.id, alan.id}

    def test_not_paginated_and_includes_institution(self, auth_client):
        inst = Institution.objects.create(name="Biohub")
        ada = Person.objects.create(given_name="Ada", family_name="Lovelace", institution=inst)

        response = auth_client.get(f"/people/v1/people/by-ids/?ids={ada.id}")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert data[0]["institution"]["name"] == "Biohub"

    def test_unknown_ids_skipped(self, auth_client):
        ada = Person.objects.create(given_name="Ada", family_name="Lovelace")

        response = auth_client.get(f"/people/v1/people/by-ids/?ids={ada.id},999999")
        assert response.status_code == 200
        assert {p["id"] for p in response.json()} == {ada.id}

    def test_missing_ids_returns_400(self, auth_client):
        assert auth_client.get("/people/v1/people/by-ids/").status_code == 400

    def test_non_integer_id_returns_400(self, auth_client):
        assert auth_client.get("/people/v1/people/by-ids/?ids=notanint").status_code == 400

    def test_requires_authentication(self):
        client = APIClient()
        assert client.get("/people/v1/people/by-ids/?ids=1", HTTP_ACCEPT="application/json").status_code == 401


@pytest.mark.django_db
class TestInstitutionCrud:
    def test_create_and_search(self, auth_client):
        create = auth_client.post("/people/v1/institutions/", data={"name": "Test"}, format="json")
        assert create.status_code == 201, create.content
        auth_client.post("/people/v1/institutions/", data={"name": "Stanford University"}, format="json")

        response = auth_client.get("/people/v1/institutions/?search=Test")
        results = response.json()["results"]
        assert len(results) == 1
        assert results[0]["name"] == "Test"

    def test_delete_unreferenced_institution(self, auth_client):
        inst = Institution.objects.create(name="Stanford University")
        response = auth_client.delete(f"/people/v1/institutions/{inst.id}/")
        assert response.status_code == 204
        assert not Institution.objects.filter(id=inst.id).exists()

    def test_delete_referenced_institution_nulls_people(self, auth_client):
        inst = Institution.objects.create(name="Biohub")
        person = Person.objects.create(given_name="Ada", family_name="Lovelace", institution=inst)

        response = auth_client.delete(f"/people/v1/institutions/{inst.id}/")
        assert response.status_code == 204
        # SET_NULL: the institution is gone, the person is kept with no institution
        assert not Institution.objects.filter(id=inst.id).exists()
        person.refresh_from_db()
        assert person.institution is None


@pytest.mark.django_db
class TestPersonInstitutionLink:
    def test_set_institution_via_patch(self, auth_client):
        person = Person.objects.create(given_name="Ada", family_name="Lovelace")
        inst = Institution.objects.create(name="Biohub")

        response = auth_client.patch(
            f"/people/v1/people/{person.id}/",
            data={"institution_id": inst.id},
            format="json",
        )
        assert response.status_code == 200, response.content
        person.refresh_from_db()
        assert person.institution_id == inst.id

    def test_clear_institution_via_patch(self, auth_client):
        inst = Institution.objects.create(name="Biohub")
        person = Person.objects.create(given_name="Ada", family_name="Lovelace", institution=inst)

        response = auth_client.patch(
            f"/people/v1/people/{person.id}/",
            data={"institution_id": None},
            format="json",
        )
        assert response.status_code == 200, response.content
        person.refresh_from_db()
        assert person.institution is None
