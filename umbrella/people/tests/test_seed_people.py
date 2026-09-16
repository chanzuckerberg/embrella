"""Tests for the seed_people management command."""

from io import StringIO
from unittest import mock

import pytest
from django.contrib.auth.models import User
from django.core.management import call_command

from people.models import Person


def _run(**kwargs):
    out = StringIO()
    call_command("seed_people", stdout=out, **kwargs)
    return out.getvalue()


@pytest.mark.django_db
class TestSeedPeople:
    def test_creates_a_person_per_active_user(self):
        User.objects.create_user("ada", email="ada@x.org", first_name="Ada", last_name="Lovelace")
        User.objects.create_user("alan", email="alan@x.org", first_name="Alan", last_name="Turing")

        _run()

        assert Person.objects.count() == 2
        ada = Person.objects.get(user__username="ada")
        assert (ada.given_name, ada.family_name, ada.contact_email) == ("Ada", "Lovelace", "ada@x.org")

    def test_is_idempotent(self):
        User.objects.create_user("ada", first_name="Ada", last_name="Lovelace")
        _run()
        _run()  # second run must not duplicate
        assert Person.objects.count() == 1

    def test_falls_back_to_username_when_no_name(self):
        User.objects.create_user("nameless")
        _run()
        person = Person.objects.get(user__username="nameless")
        assert person.given_name == "nameless"
        assert person.family_name == ""

    def test_skips_inactive_users(self):
        User.objects.create_user("ghost", first_name="Ghost", is_active=False)
        _run()
        assert Person.objects.count() == 0

    def test_dry_run_writes_nothing(self):
        User.objects.create_user("ada", first_name="Ada", last_name="Lovelace")
        out = _run(dry_run=True)
        assert Person.objects.count() == 0
        assert "would create" in out.lower()

    def test_links_existing_unlinked_person_by_email(self):
        # Someone was added manually before their account was seeded.
        person = Person.objects.create(given_name="Ada", family_name="Lovelace", contact_email="ada@x.org")
        user = User.objects.create_user("ada", email="Ada@X.org", first_name="Ada", last_name="Lovelace")

        _run()

        assert Person.objects.count() == 1  # linked, not duplicated (email match is case-insensitive)
        person.refresh_from_db()
        assert person.user == user

    def test_same_email_across_two_users_links_once_then_creates(self):
        Person.objects.create(given_name="Ada", family_name="Lovelace", contact_email="ada@x.org")
        u1 = User.objects.create_user("ada1", email="ada@x.org")
        u2 = User.objects.create_user("ada2", email="ada@x.org")

        _run()

        # First user links the existing row; the second has none left to grab, so it creates one.
        assert Person.objects.count() == 2
        assert Person.objects.get(user=u1).given_name == "Ada"  # linked the manual row
        assert Person.objects.filter(user=u2).exists()  # got its own new row

    def test_links_by_email_shaped_username_when_email_blank(self):
        # Older accounts: blank User.email, username is the email.
        person = Person.objects.create(given_name="Ada", family_name="Lovelace", contact_email="ada@x.org")
        user = User.objects.create_user("ada@x.org")  # email defaults to ""

        _run()

        assert Person.objects.count() == 1  # linked via the username, not duplicated
        person.refresh_from_db()
        assert person.user == user

    def test_warns_when_multiple_unlinked_share_an_email(self):
        Person.objects.create(given_name="Ada", family_name="L", contact_email="ada@x.org")
        Person.objects.create(given_name="Ada", family_name="Dup", contact_email="ada@x.org")
        User.objects.create_user("ada", email="ada@x.org")

        err = StringIO()
        call_command("seed_people", stdout=StringIO(), stderr=err)

        assert "share ada@x.org" in err.getvalue().lower()
        assert Person.objects.filter(user__isnull=True).count() == 1  # oldest linked, other left alone

    def test_one_failing_user_does_not_abort_the_rest(self):
        User.objects.create_user("ada", first_name="Ada")
        User.objects.create_user("bob", first_name="Bob")
        real_create = Person.objects.create

        def flaky(**kwargs):
            if kwargs["user"].username == "ada":
                raise ValueError("boom")
            return real_create(**kwargs)

        err = StringIO()
        with mock.patch.object(Person.objects, "create", side_effect=flaky):
            call_command("seed_people", stdout=StringIO(), stderr=err)

        assert Person.objects.filter(user__username="bob").exists()  # the loop kept going
        assert not Person.objects.filter(user__username="ada").exists()
        assert "skipped ada" in err.getvalue().lower()

    def test_dry_run_link_writes_nothing(self):
        person = Person.objects.create(given_name="Ada", family_name="Lovelace", contact_email="ada@x.org")
        User.objects.create_user("ada", email="ada@x.org")

        out = _run(dry_run=True)

        person.refresh_from_db()
        assert person.user is None  # not attached on a dry run
        assert "would link" in out.lower()

    def test_blank_email_never_attaches(self):
        # An unlinked row with no email must not be attached to a user with no email.
        Person.objects.create(given_name="Someone", family_name="", contact_email="")
        User.objects.create_user("nameless")

        _run()

        assert Person.objects.count() == 2  # a new row is created, the blank one is left alone
        assert Person.objects.filter(user__isnull=True, contact_email="").count() == 1
