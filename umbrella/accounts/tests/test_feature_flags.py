"""Tests for the system + per-user feature-flag layer (accounts.feature_flags)."""

import pytest
from django.contrib.auth.models import AnonymousUser, User
from rest_framework.test import APIClient

from accounts.feature_flags import enabled_flags_for, is_feature_enabled
from accounts.models import Profile, SystemFeatureFlag


@pytest.fixture
def user(db):
    return User.objects.create_user(username="flaguser@example.com")


@pytest.mark.django_db
class TestIsFeatureEnabled:
    def test_global_flag_on_enables_for_everyone(self, user):
        SystemFeatureFlag.objects.create(name="deposition", enabled=True)
        assert is_feature_enabled(user, "deposition") is True
        assert is_feature_enabled(AnonymousUser(), "deposition") is True

    def test_global_off_and_no_override_is_disabled(self, user):
        SystemFeatureFlag.objects.create(name="deposition", enabled=False)
        assert is_feature_enabled(user, "deposition") is False

    def test_unknown_flag_is_disabled(self, user):
        assert is_feature_enabled(user, "does_not_exist") is False

    def test_per_user_override_enables_when_global_off(self, user):
        # No global row (off); the user opts in via their profile.
        user.profile.feature_flags = {"deposition": True}
        user.profile.save()
        assert is_feature_enabled(user, "deposition") is True
        # Other users without the override stay disabled.
        other = User.objects.create_user(username="other@example.com")
        assert is_feature_enabled(other, "deposition") is False

    def test_anonymous_user_has_no_override(self):
        assert is_feature_enabled(AnonymousUser(), "deposition") is False

    def test_missing_profile_does_not_raise(self, user):
        # Existing users may have no Profile yet (lazy creation) — must not crash.
        Profile.objects.filter(user=user).delete()
        user.refresh_from_db()
        assert is_feature_enabled(user, "deposition") is False


@pytest.mark.django_db
class TestEnabledFlagsFor:
    def test_union_of_global_and_overrides_sorted(self, user):
        SystemFeatureFlag.objects.create(name="alpha", enabled=True)
        SystemFeatureFlag.objects.create(name="zeta", enabled=False)
        user.profile.feature_flags = {"zeta": True, "gamma": False}
        user.profile.save()
        # alpha (global on) + zeta (override on); gamma override is false -> excluded.
        assert enabled_flags_for(user) == ["alpha", "zeta"]

    def test_anonymous_returns_only_global(self):
        SystemFeatureFlag.objects.create(name="alpha", enabled=True)
        assert enabled_flags_for(AnonymousUser()) == ["alpha"]


@pytest.mark.django_db
class TestUserEndpointFlags:
    def test_user_endpoint_includes_enabled_flags(self, user):
        SystemFeatureFlag.objects.create(name="deposition", enabled=True)
        client = APIClient()
        client.force_login(user)
        r = client.get("/user")
        assert r.status_code == 200
        assert "deposition" in r.json()["feature_flags"]

    def test_user_endpoint_unauthenticated_is_401(self):
        assert APIClient().get("/user").status_code == 401
