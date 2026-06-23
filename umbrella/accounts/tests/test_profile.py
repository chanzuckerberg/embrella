"""Tests for accounts.Profile and its auto-creation signal."""

import pytest
from django.contrib.auth.models import User

from accounts.models import Profile


@pytest.mark.django_db
class TestProfileAutoCreation:
    def test_profile_created_on_user_creation(self):
        user = User.objects.create_user(username="alice@example.com")
        assert Profile.objects.filter(user=user).exists()
        assert user.profile.feature_flags == {}
        assert user.profile.orcid_authenticated == ""

    def test_no_duplicate_profile_on_user_save(self):
        user = User.objects.create_user(username="bob@example.com")
        user.email = "bob@example.com"
        user.save()
        assert Profile.objects.filter(user=user).count() == 1


@pytest.mark.django_db
class TestProfileFeatureFlags:
    def test_feature_flags_round_trip(self):
        user = User.objects.create_user(username="carol@example.com")
        profile = user.profile
        profile.feature_flags = {"beta_ui": True, "experimental_export": False}
        profile.save()

        profile.refresh_from_db()
        assert profile.feature_flags == {"beta_ui": True, "experimental_export": False}

    def test_orcid_authenticated_persists(self):
        user = User.objects.create_user(username="dave@example.com")
        profile = user.profile
        profile.orcid_authenticated = "0000-0002-1825-0097"
        profile.save()

        profile.refresh_from_db()
        assert profile.orcid_authenticated == "0000-0002-1825-0097"
