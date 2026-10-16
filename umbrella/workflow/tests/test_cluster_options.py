"""Clusters come from stores.Cluster and ProcSoftware, never from processor classes."""

import pytest
from django.apps import apps
from django.contrib.auth.models import User
from processes.models import ProcSoftware
from processes.services.cluster_resolver import active_cluster_ids, clear_default_cluster_cache, get_default_cluster_id
from stores.models import Cluster

pytestmark = pytest.mark.django_db

PROCESSOR = "aretomo3"


@pytest.fixture
def site_cluster():
    cluster, _ = Cluster.objects.update_or_create(
        cluster_id="site-x",
        defaults={"name": "Site X", "http_base_url": "https://site-x.example/", "ssh_hostname": "x"},
    )
    clear_default_cluster_cache()
    yield cluster
    clear_default_cluster_cache()


@pytest.fixture
def logged_in(client):
    client.force_login(User.objects.create_user(username="cluster-tester"))
    return client


def _software(**fields):
    software, _ = ProcSoftware.objects.update_or_create(
        processor_class=PROCESSOR,
        defaults={"name": PROCESSOR, "active": True, **fields},
    )
    return software


def test_list_clusters_returns_active_only(logged_in, site_cluster):
    Cluster.objects.update_or_create(
        cluster_id="site-off",
        defaults={"name": "Off", "http_base_url": "https://off.example/", "ssh_hostname": "x", "is_active": False},
    )

    response = logged_in.get("/workflow/v1/clusters/")

    assert response.status_code == 200
    ids = [c["cluster_id"] for c in response.json()["clusters"]]
    assert "site-x" in ids
    assert "site-off" not in ids


def test_schema_falls_back_to_site_clusters(logged_in, site_cluster):
    # Empty DB values: site default cluster, every active cluster allowed.
    _software(default_cluster=None, allowed_clusters=[])

    data = logged_in.get(f"/workflow/v1/processors/{PROCESSOR}/schema/").json()

    assert data["default_cluster"] == get_default_cluster_id()
    assert sorted(data["allowed_clusters"]) == sorted(active_cluster_ids())


def test_schema_uses_software_clusters(logged_in, site_cluster):
    _software(default_cluster="site-x", allowed_clusters=["site-x"])

    data = logged_in.get(f"/workflow/v1/processors/{PROCESSOR}/schema/").json()

    assert data["default_cluster"] == "site-x"
    assert data["allowed_clusters"] == ["site-x"]


def test_startup_sync_keeps_admin_clusters(site_cluster):
    software = _software(default_cluster="site-x", allowed_clusters=["site-x"])

    apps.get_app_config("workflow")._sync_processors_to_database()

    software.refresh_from_db()
    assert software.default_cluster == "site-x"
    assert software.allowed_clusters == ["site-x"]
