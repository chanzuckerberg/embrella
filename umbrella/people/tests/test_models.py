"""Model-level tests for the people directory app."""

import pytest
from django.contrib.auth.models import User
from django.db import IntegrityError, transaction

from people.models import Institution, Person


@pytest.mark.django_db
class TestPersonOrcid:
    def test_multiple_people_without_orcid_allowed(self):
        """null=True means many records without an ORCID don't collide on the unique constraint."""
        Person.objects.create(given_name="Ada", family_name="Lovelace")
        Person.objects.create(given_name="Alan", family_name="Turing")
        assert Person.objects.filter(orcid__isnull=True).count() == 2

    def test_duplicate_orcid_rejected(self):
        Person.objects.create(given_name="Ada", family_name="Lovelace", orcid="0000-0002-1825-0097")
        with pytest.raises(IntegrityError), transaction.atomic():
            Person.objects.create(given_name="Grace", family_name="Hopper", orcid="0000-0002-1825-0097")


@pytest.mark.django_db
class TestPersonUserLink:
    def test_user_link_optional(self):
        person = Person.objects.create(given_name="Ada", family_name="Lovelace")
        assert person.user is None

    def test_user_link_set_null_on_user_delete(self):
        user = User.objects.create_user(username="ada@example.com")
        person = Person.objects.create(given_name="Ada", family_name="Lovelace", user=user)
        user.delete()
        person.refresh_from_db()
        assert person.user is None


@pytest.mark.django_db
class TestPersonInstitution:
    def test_institution_optional(self):
        person = Person.objects.create(given_name="Ada", family_name="Lovelace")
        assert person.institution is None

    def test_institution_links_person(self):
        inst = Institution.objects.create(name="Biohub")
        person = Person.objects.create(given_name="Ada", family_name="Lovelace", institution=inst)

        assert person.institution == inst
        assert list(inst.people.all()) == [person]

    def test_institution_set_null_on_delete(self):
        inst = Institution.objects.create(name="Biohub")
        person = Person.objects.create(given_name="Ada", family_name="Lovelace", institution=inst)
        # on_delete=SET_NULL: deleting an institution severs the link but keeps the person.
        inst.delete()
        person.refresh_from_db()
        assert person.institution is None
        assert Person.objects.filter(id=person.id).exists()
