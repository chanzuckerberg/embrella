"""
Tests for workflow.views.ssh_views — focus on credential persistence.
"""

import base64
import json
from unittest.mock import patch

import pytest
from django.contrib.auth.models import User
from rest_framework.test import APIRequestFactory, force_authenticate
from stores.models import Cluster
from users.models import UserClusterCredentials
from workflow.views.ssh_views import check_ssh_setup, setup_ssh_key


@pytest.fixture
def user(db):
    return User.objects.create_user(username="dora@example.com", email="dora@example.com")


@pytest.fixture
def factory():
    return APIRequestFactory()


@pytest.mark.django_db
class TestSetupSshKeyPersistsCredentials:
    @patch("common.clusterio.setup_ssh_key_for_user")
    def test_persists_on_success(self, mock_setup, factory, user):
        mock_setup.return_value = {
            "success": True,
            "message": "ok",
            "can_connect": True,
            "error": None,
        }

        request = factory.post(
            "/workflow/v1/ssh/setup_key/",
            data=json.dumps({
                "cluster_id": "bruno",
                "username": "dora-bruno",
                "password": base64.b64encode(b"hunter2").decode("utf-8"),
            }),
            content_type="application/json",
        )
        force_authenticate(request, user=user)

        response = setup_ssh_key(request)

        assert response.status_code == 200
        cluster = Cluster.objects.get(cluster_id="bruno")
        row = UserClusterCredentials.objects.get(user=user, cluster=cluster)
        assert row.username == "dora-bruno"

    @patch("common.clusterio.setup_ssh_key_for_user")
    def test_update_or_create_on_resubmit(self, mock_setup, factory, user):
        mock_setup.return_value = {
            "success": True,
            "message": "ok",
            "can_connect": True,
            "error": None,
        }
        cluster = Cluster.objects.get(cluster_id="bruno")
        UserClusterCredentials.objects.create(user=user, cluster=cluster, username="old-name")
        previous_updated_at = UserClusterCredentials.objects.get(user=user, cluster=cluster).updated_at

        request = factory.post(
            "/workflow/v1/ssh/setup_key/",
            data=json.dumps({
                "cluster_id": "bruno",
                "username": "new-name",
                "password": base64.b64encode(b"hunter2").decode("utf-8"),
            }),
            content_type="application/json",
        )
        force_authenticate(request, user=user)

        setup_ssh_key(request)

        row = UserClusterCredentials.objects.get(user=user, cluster=cluster)
        assert row.username == "new-name"
        assert row.updated_at > previous_updated_at
        assert UserClusterCredentials.objects.filter(user=user, cluster=cluster).count() == 1

    @patch("common.clusterio.setup_ssh_key_for_user")
    def test_does_not_persist_on_failure(self, mock_setup, factory, user):
        mock_setup.return_value = {
            "success": False,
            "message": "auth failed",
            "can_connect": False,
            "error": "Invalid credentials",
        }

        request = factory.post(
            "/workflow/v1/ssh/setup_key/",
            data=json.dumps({
                "cluster_id": "bruno",
                "username": "dora-bruno",
                "password": base64.b64encode(b"wrong").decode("utf-8"),
            }),
            content_type="application/json",
        )
        force_authenticate(request, user=user)

        setup_ssh_key(request)

        cluster = Cluster.objects.get(cluster_id="bruno")
        assert not UserClusterCredentials.objects.filter(user=user, cluster=cluster).exists()


@pytest.mark.django_db
class TestCheckSshSetupReturnsResolvedUsername:
    def test_no_credentials_returns_setup_required_with_null_username(self, factory, user):
        request = factory.post(
            "/workflow/v1/ssh/check_setup/",
            data=json.dumps({"cluster_id": "bruno"}),
            content_type="application/json",
        )
        force_authenticate(request, user=user)

        response = check_ssh_setup(request)
        body = json.loads(response.content)

        assert body["setup_required"] is True
        assert body["username"] is None

    @patch("common.clusterio.test_ssh_as_user")
    def test_with_credentials_resolves_username(self, mock_test, factory, user):
        cluster = Cluster.objects.get(cluster_id="bruno")
        UserClusterCredentials.objects.create(user=user, cluster=cluster, username="dora-bruno")
        mock_test.return_value = {
            "can_connect": True,
            "error": None,
            "cluster_id": "bruno",
            "username": "dora-bruno",
        }

        request = factory.post(
            "/workflow/v1/ssh/check_setup/",
            data=json.dumps({"cluster_id": "bruno"}),
            content_type="application/json",
        )
        force_authenticate(request, user=user)

        response = check_ssh_setup(request)
        body = json.loads(response.content)

        assert body["setup_required"] is False
        assert body["username"] == "dora-bruno"
        mock_test.assert_called_once_with("dora-bruno", "bruno")
