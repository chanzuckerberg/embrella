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
    @pytest.fixture(autouse=True)
    def _no_seeded_flags(self, db):
        # Migration 0005 seeds rows (example/review/...); these tests control the
        # full flag set themselves, so start from a clean slate. The delete is
        # rolled back with the per-test transaction, so seeds survive elsewhere.
        SystemFeatureFlag.objects.all().delete()

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

    def test_per_user_override_off_wins_over_global_on(self, user):
        # Precedence: an explicit False override disables a globally-on flag.
        SystemFeatureFlag.objects.create(name="deposition", enabled=True)
        user.profile.feature_flags = {"deposition": False}
        user.profile.save()
        assert is_feature_enabled(user, "deposition") is False
        # A user without the override still sees the global on.
        other = User.objects.create_user(username="other@example.com")
        assert is_feature_enabled(other, "deposition") is True

    def test_absent_override_key_falls_back_to_global(self, user):
        # A profile dict that doesn't mention the flag falls through to the global.
        SystemFeatureFlag.objects.create(name="deposition", enabled=True)
        user.profile.feature_flags = {"something_else": False}
        user.profile.save()
        assert is_feature_enabled(user, "deposition") is True

    def test_anonymous_user_has_no_override(self):
        assert is_feature_enabled(AnonymousUser(), "deposition") is False

    def test_missing_profile_does_not_raise(self, user):
        # Existing users may have no Profile yet (lazy creation) — must not crash.
        Profile.objects.filter(user=user).delete()
        user.refresh_from_db()
        assert is_feature_enabled(user, "deposition") is False


@pytest.mark.django_db
class TestEnabledFlagsFor:
    @pytest.fixture(autouse=True)
    def _no_seeded_flags(self, db):
        SystemFeatureFlag.objects.all().delete()

    def test_union_of_global_and_overrides_sorted(self, user):
        SystemFeatureFlag.objects.create(name="alpha", enabled=True)
        SystemFeatureFlag.objects.create(name="zeta", enabled=False)
        user.profile.feature_flags = {"zeta": True, "gamma": False}
        user.profile.save()
        # alpha (global on) + zeta (override on); gamma override is false -> excluded.
        assert enabled_flags_for(user) == ["alpha", "zeta"]

    def test_override_off_removes_globally_on_flag(self, user):
        # Precedence: a False override drops a flag that is on globally.
        SystemFeatureFlag.objects.create(name="alpha", enabled=True)
        SystemFeatureFlag.objects.create(name="beta", enabled=True)
        user.profile.feature_flags = {"alpha": False}
        user.profile.save()
        assert enabled_flags_for(user) == ["beta"]

    def test_anonymous_returns_only_global(self):
        SystemFeatureFlag.objects.create(name="alpha", enabled=True)
        assert enabled_flags_for(AnonymousUser()) == ["alpha"]


@pytest.mark.django_db
class TestUserEndpointFlags:
    @pytest.fixture(autouse=True)
    def _no_seeded_flags(self, db):
        SystemFeatureFlag.objects.all().delete()

    def test_user_endpoint_includes_enabled_flags(self, user):
        SystemFeatureFlag.objects.create(name="deposition", enabled=True)
        client = APIClient()
        client.force_login(user)
        r = client.get("/user")
        assert r.status_code == 200
        assert "deposition" in r.json()["feature_flags"]

    def test_user_endpoint_unauthenticated_is_401(self):
        assert APIClient().get("/user").status_code == 401


@pytest.mark.django_db
def test_seed_migration_enables_launched_flags():
    # Migration 0005 seeds the flags mirroring the frontend FEATURE_FLAG enum,
    # with the previously-hardcoded launched flags on and the rest off.
    flags = dict(SystemFeatureFlag.objects.values_list("name", "enabled"))
    assert flags["review"] is True
    assert flags["manage_data"] is False
    assert flags["deposition"] is False
