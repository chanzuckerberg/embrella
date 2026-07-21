"""Tests for Cluster default resolution, the cached default-cluster id, and the
file-server base-URL allowlist.
"""

from unittest.mock import Mock

import pytest
from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from processes.services.cluster_resolver import (
    NoDefaultClusterError,
    clear_default_cluster_cache,
    get_default_cluster_id,
)
from tem.models import MsiSession

from stores.models import Cluster, resolve_review_path, validate_fileserver_base_url

pytestmark = pytest.mark.django_db


def _make_cluster(cluster_id, **kwargs):
    kwargs.setdefault("name", cluster_id.upper())
    kwargs.setdefault("http_base_url", f"https://{cluster_id}.example/")
    kwargs.setdefault("ssh_hostname", "host")
    return Cluster.objects.create(cluster_id=cluster_id, **kwargs)


class ClusterGetDefaultTests(TestCase):
    def setUp(self):
        # start from a known-empty set.
        Cluster.objects.all().delete()
        clear_default_cluster_cache()

    def tearDown(self):
        clear_default_cluster_cache()

    def test_returns_flagged_default(self):
        _make_cluster("aaa")
        flagged = _make_cluster("zzz", is_default=True)
        self.assertEqual(Cluster.get_default(), flagged)

    def test_falls_back_to_first_active_alphabetical(self):
        _make_cluster("zzz")
        _make_cluster("aaa")
        self.assertEqual(Cluster.get_default().cluster_id, "aaa")

    def test_fallback_ignores_inactive(self):
        _make_cluster("aaa", is_active=False)
        _make_cluster("bbb")
        self.assertEqual(Cluster.get_default().cluster_id, "bbb")

    def test_none_when_no_clusters(self):
        self.assertIsNone(Cluster.get_default())

    def test_save_enforces_single_default(self):
        first = _make_cluster("aaa", is_default=True)
        second = _make_cluster("bbb", is_default=True)
        first.refresh_from_db()
        second.refresh_from_db()
        self.assertFalse(first.is_default)
        self.assertTrue(second.is_default)
        self.assertEqual(Cluster.objects.filter(is_default=True).count(), 1)


class DefaultClusterIdTests(TestCase):
    def setUp(self):
        Cluster.objects.all().delete()
        clear_default_cluster_cache()

    def tearDown(self):
        clear_default_cluster_cache()

    def test_raises_when_no_default(self):
        with self.assertRaises(NoDefaultClusterError):
            get_default_cluster_id()

    def test_returns_default_id(self):
        _make_cluster("demo", is_default=True)
        self.assertEqual(get_default_cluster_id(), "demo")

    def test_cache_invalidated_on_cluster_change(self):
        _make_cluster("demo", is_default=True)
        self.assertEqual(get_default_cluster_id(), "demo")  # populate cache
        # A new default fires the post_save signal wired in ProcessesConfig.ready(),
        # which must clear the cache so the next call reflects the change.
        _make_cluster("demo2", is_default=True)
        self.assertEqual(get_default_cluster_id(), "demo2")


class FileserverAllowlistTests(TestCase):
    def test_empty_allowlist_is_noop(self):
        with override_settings(FILESERVER_ALLOWED_HOSTS=[]):
            validate_fileserver_base_url("http://anything.example/")  # no raise

    def test_allowed_origin_passes(self):
        with override_settings(FILESERVER_ALLOWED_HOSTS=["http://localhost:8080", "https://good.example"]):
            validate_fileserver_base_url("http://localhost:8080/tomodata/")
            validate_fileserver_base_url("https://good.example/x.jpeg")

    def test_disallowed_origin_raises(self):
        with override_settings(FILESERVER_ALLOWED_HOSTS=["http://localhost:8080"]), self.assertRaises(ValidationError):
            validate_fileserver_base_url("https://evil.example/x")

    def test_ssrf_metadata_host_blocked(self):
        with override_settings(FILESERVER_ALLOWED_HOSTS=["https://good.example"]), self.assertRaises(ValidationError):
            validate_fileserver_base_url("http://169.254.169.254/latest/meta-data/")

    def test_same_host_wrong_port_blocked(self):
        with override_settings(FILESERVER_ALLOWED_HOSTS=["http://localhost:8080"]), self.assertRaises(ValidationError):
            validate_fileserver_base_url("http://localhost:9000/")

    def test_cluster_clean_enforces_allowlist(self):
        with override_settings(FILESERVER_ALLOWED_HOSTS=["https://ok.example"]):
            cluster = Cluster(cluster_id="x", name="X", http_base_url="https://evil.example/", ssh_hostname="h")
            with self.assertRaises(ValidationError):
                cluster.clean()
            cluster.http_base_url = "https://ok.example/"
            cluster.clean()  # allowed origin -> no raise


class ResolveReviewPathAllowlistTests(TestCase):
    """resolve_review_path re-validates the base URL, but only for URL templates."""

    def _mock_session(self):
        session = Mock(spec=MsiSession)
        session.name = "sess1"
        session.session_plan.scope.name = "Krios1"
        return session

    def test_url_template_enforces_allowlist(self):
        cluster = Cluster(cluster_id="x", name="X", http_base_url="https://evil.example/", ssh_hostname="h")
        with override_settings(FILESERVER_ALLOWED_HOSTS=["https://ok.example"]), self.assertRaises(ValidationError):
            resolve_review_path(
                "zarr_url",
                cluster,
                self._mock_session(),
                workflow="aretomo3",
                run="001",
                vol_suffix="vol003",
                position="P1",
            )

    def test_filesystem_template_skips_allowlist(self):
        # proc_dir has no {http_base}; a disallowed base URL must not block it.
        cluster = Cluster(cluster_id="x", name="X", http_base_url="https://evil.example/", ssh_hostname="h")
        with override_settings(FILESERVER_ALLOWED_HOSTS=["https://ok.example"]):
            path = resolve_review_path("proc_dir", cluster, self._mock_session(), workflow="aretomo3", run="001")
        self.assertIn("aretomo3", path)
