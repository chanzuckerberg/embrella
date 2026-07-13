"""Tests for the allauth adapters, focused on username generation."""

import pytest
from django.contrib.auth.models import User

from umbrella.adapters import UmbrellaAccountAdapter


def _populate(first_name="", last_name="", email=""):
    adapter = UmbrellaAccountAdapter()
    user = User(first_name=first_name, last_name=last_name, email=email)
    adapter.populate_username(request=None, user=user)
    return user.username


@pytest.mark.django_db
class TestPopulateUsername:
    def test_first_and_last_name(self):
        # allauth normalizes candidates to lowercase ASCII.
        assert _populate("Test", "Me", "Test.Me@example.com") == "test.me"

    def test_collision_gets_suffix(self):
        User.objects.create(username="test.me")
        username = _populate("Test", "Me", "Test.Me@example.com")
        assert username != "test.me"
        assert username.startswith("test.me")

    def test_missing_last_name_falls_back_to_email_local_part(self):
        assert _populate("Test", "", "this.part@example.com") == "this.part"

    def test_no_names_falls_back_to_email_local_part(self):
        assert _populate("", "", "this.part@example.com") == "this.part"

    def test_existing_username_preserved(self):
        adapter = UmbrellaAccountAdapter()
        user = User(username="preset", first_name="Test", last_name="Me")
        adapter.populate_username(request=None, user=user)
        assert user.username == "preset"
