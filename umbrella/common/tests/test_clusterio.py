"""
Tests for common.clusterio module.

Tests SSH connection utilities and authentication helpers.
"""

from unittest.mock import MagicMock, patch

import pytest
from accounts.cluster_usernames import MissingClusterCredentialsError, clear_username_cache
from accounts.models import UserClusterCredentials
from django.contrib.auth.models import User
from stores.models import Cluster

from common import clusterio


@pytest.mark.django_db
class TestGetAuthForUser:
    """Tests for the get_auth_for_user helper.

    NOTE: These tests hit the `stores.Cluster` table (via `_cluster_exists`) which is
    seeded by migration `stores.0010_seed_clusters`, so czii/bruno rows exist.
    Covers the credential lookup path: a Django User + cluster_id resolves
    via UserClusterCredentials. Missing rows raise
    MissingClusterCredentialsError so callers surface the standard
    ssh_setup_required 403 contract.
    """

    @pytest.fixture(autouse=True)
    def _clear_caches(self):
        clusterio.clear_cluster_cache()
        clear_username_cache()
        yield
        clusterio.clear_cluster_cache()
        clear_username_cache()

    @pytest.fixture
    def user(self, db):
        return User.objects.create_user(username="alice@example.com", email="alice@example.com")

    @pytest.fixture
    def czii(self, db):
        return Cluster.objects.get(cluster_id="czii")

    @patch("common.clusterio.get_auth_service_user")
    def test_resolves_persisted_username(self, mock_service_auth, user, czii):
        """When credentials exist, auth uses the persisted cluster username."""
        UserClusterCredentials.objects.create(user=user, cluster=czii, username="alice123")
        mock_service_auth.return_value = {"username": "service-user", "pkey": MagicMock()}

        auth, error = clusterio.get_auth_for_user(user, "czii")

        assert error is None
        assert auth["username"] == "alice123"
        assert "pkey" in auth

    def test_missing_credentials_raises(self, user):
        """No row → MissingClusterCredentialsError; callers map to 403."""
        with pytest.raises(MissingClusterCredentialsError):
            clusterio.get_auth_for_user(user, "czii")

    def test_invalid_cluster_returns_error_dict(self, user):
        """Unknown cluster_id is a request error, not a missing-credentials error."""
        auth, error = clusterio.get_auth_for_user(user, "nonexistent")
        assert auth is None
        assert error is not None
        assert "Invalid cluster_id" in error["error"]
        assert error["ssh_setup_required"] is False

    @patch("common.clusterio.get_auth_service_user")
    def test_does_not_mutate_cached_service_auth(self, mock_service_auth, user, czii):
        """Building per-user auth must not mutate the shared service-user dict."""
        UserClusterCredentials.objects.create(user=user, cluster=czii, username="alice123")
        cached = {"username": "service-user", "pkey": MagicMock()}
        mock_service_auth.return_value = cached

        clusterio.get_auth_for_user(user, "czii")

        assert cached["username"] == "service-user"
