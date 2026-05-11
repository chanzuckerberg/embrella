"""
Tests for users.usernames helper.
NOTE: depends on `stores.Cluster` table seeded by migration `stores.0010_seed_clusters`, so czii/bruno rows exist.
"""

import pytest
from django.contrib.auth.models import AnonymousUser, User
from stores.models import Cluster

from users.models import UserClusterCredentials
from users.usernames import (
    MissingClusterCredentialsError,
    clear_username_cache,
    format_cluster_username_for_display,
    resolve_cluster_username,
)


@pytest.mark.django_db
class TestResolveClusterUsername:
    @pytest.fixture(autouse=True)
    def _clear_cache(self):
        clear_username_cache()
        yield
        clear_username_cache()

    @pytest.fixture
    def user(self, db):
        return User.objects.create_user(username="bob@example.com", email="bob@example.com")

    @pytest.fixture
    def czii(self, db):
        return Cluster.objects.get(cluster_id="czii")

    def test_returns_persisted_username(self, user, czii):
        UserClusterCredentials.objects.create(user=user, cluster=czii, username="bobby")
        assert resolve_cluster_username(user, "czii") == "bobby"

    def test_raises_when_no_row(self, user):
        with pytest.raises(MissingClusterCredentialsError):
            resolve_cluster_username(user, "czii")

    def test_raises_for_anonymous_user(self):
        with pytest.raises(MissingClusterCredentialsError):
            resolve_cluster_username(AnonymousUser(), "czii")

    def test_per_cluster_independence(self, user, czii):
        bruno = Cluster.objects.get(cluster_id="bruno")
        UserClusterCredentials.objects.create(user=user, cluster=czii, username="bob_czii")
        UserClusterCredentials.objects.create(user=user, cluster=bruno, username="bob_bruno")
        assert resolve_cluster_username(user, "czii") == "bob_czii"
        assert resolve_cluster_username(user, "bruno") == "bob_bruno"

    def test_signal_invalidates_cache_on_save(self, user, czii):
        with pytest.raises(MissingClusterCredentialsError):
            resolve_cluster_username(user, "czii")
        UserClusterCredentials.objects.create(user=user, cluster=czii, username="bobby")
        assert resolve_cluster_username(user, "czii") == "bobby"

    def test_signal_invalidates_cache_on_update(self, user, czii):
        row = UserClusterCredentials.objects.create(user=user, cluster=czii, username="old")
        assert resolve_cluster_username(user, "czii") == "old"
        row.username = "new"
        row.save()
        assert resolve_cluster_username(user, "czii") == "new"

    def test_signal_invalidates_cache_on_delete(self, user, czii):
        row = UserClusterCredentials.objects.create(user=user, cluster=czii, username="bobby")
        assert resolve_cluster_username(user, "czii") == "bobby"
        row.delete()
        with pytest.raises(MissingClusterCredentialsError):
            resolve_cluster_username(user, "czii")


@pytest.mark.django_db
class TestFormatClusterUsernameForDisplay:
    @pytest.fixture(autouse=True)
    def _clear_cache(self):
        clear_username_cache()
        yield
        clear_username_cache()

    @pytest.fixture
    def user(self, db):
        return User.objects.create_user(username="carol@example.com", email="carol@example.com")

    def test_returns_persisted_username(self, user):
        czii = Cluster.objects.get(cluster_id="czii")
        UserClusterCredentials.objects.create(user=user, cluster=czii, username="carol123")
        assert format_cluster_username_for_display(user, "czii") == "carol123"

    def test_returns_empty_string_when_missing(self, user):
        assert format_cluster_username_for_display(user, "czii") == ""

    def test_returns_empty_string_for_anonymous_user(self):
        assert format_cluster_username_for_display(AnonymousUser(), "czii") == ""
