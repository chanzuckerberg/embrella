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


def _entry(name, *, is_dir=False, size=100, mtime=1700000000):
    """A paramiko SFTPAttributes stand-in."""
    entry = MagicMock()
    entry.filename = name
    entry.st_mode = 0o040755 if is_dir else 0o100644
    entry.st_size = size
    entry.st_mtime = mtime
    return entry


def _mock_sftp(tree):
    """Mock SSH whose sftp lists `tree`: {directory: [entries]}. stat() knows the keys."""

    def stat(path):
        if (path.rstrip("/") or "/") not in tree:
            raise FileNotFoundError(path)
        return MagicMock()

    ssh = MagicMock()
    sftp = MagicMock()
    ssh.open_sftp.return_value = sftp
    sftp.listdir_attr.side_effect = lambda d: tree[d.rstrip("/") or "/"]
    sftp.stat.side_effect = stat
    return ssh, sftp


@patch("common.clusterio.get_cluster_ssh_connection")
class TestListFiles:
    def test_flat_glob_matches_files_only(self, mock_conn):
        ssh, _ = _mock_sftp({"/data": [_entry("a.eer"), _entry("b.mdoc"), _entry("sub", is_dir=True)]})
        mock_conn.return_value = ssh

        result = clusterio.list_files("/data/", "*.eer", cluster_id="czii")

        assert result["success"] is True
        assert [f["name"] for f in result["files"]] == ["a.eer"]
        assert result["files"][0]["full_path"] == "/data/a.eer"
        assert result["total_size"] == 100

    def test_include_dirs_picks_up_zarrs(self, mock_conn):
        """A .zarr "file" is a directory -- the old always-skip-dirs rule lost every one."""
        ssh, _ = _mock_sftp({"/vol": [_entry("Position_1_Vol.zarr", is_dir=True), _entry("notes.txt")]})
        mock_conn.return_value = ssh

        without = clusterio.list_files("/vol", "*.zarr", cluster_id="czii")
        with_dirs = clusterio.list_files("/vol", "*.zarr", cluster_id="czii", include_dirs=True)

        assert without["files"] == []
        assert [f["name"] for f in with_dirs["files"]] == ["Position_1_Vol.zarr"]

    def test_multi_segment_glob_walks_matching_dirs(self, mock_conn):
        ssh, _ = _mock_sftp(
            {
                "/runs": [_entry("Position_1", is_dir=True), _entry("skipme", is_dir=True)],
                "/runs/Position_1": [_entry("dctf.zarr", is_dir=True)],
            }
        )
        mock_conn.return_value = ssh

        result = clusterio.list_files("/runs", "Position_*/*.zarr", cluster_id="czii", include_dirs=True)

        assert [f["full_path"] for f in result["files"]] == ["/runs/Position_1/dctf.zarr"]

    def test_missing_directory_reports_not_lists(self, mock_conn):
        ssh, _ = _mock_sftp({})
        mock_conn.return_value = ssh

        result = clusterio.list_files("/gone", cluster_id="czii")

        assert result["success"] is False
        assert "does not exist" in result["error"]

    def test_connections_closed(self, mock_conn):
        ssh, sftp = _mock_sftp({"/data": []})
        mock_conn.return_value = ssh

        clusterio.list_files("/data", cluster_id="czii")

        sftp.close.assert_called_once()
        ssh.close.assert_called_once()


@patch("common.clusterio.get_cluster_ssh_connection")
class TestFindPaths:
    def _ssh_returning(self, lines):
        ssh = MagicMock()
        ssh.exec_command.return_value = (MagicMock(), [line + "\n" for line in lines], MagicMock())
        return ssh

    def test_returns_stripped_paths(self, mock_conn):
        mock_conn.return_value = self._ssh_returning(["/a/x.zarr", "/a/y.zarr", ""])

        paths = clusterio.find_paths("/a", "*.zarr", cluster_id="czii", maxdepth=4)

        assert paths == ["/a/x.zarr", "/a/y.zarr"]

    def test_arguments_are_shell_quoted(self, mock_conn):
        """The whole point over an inline f-string ls/find: a path or glob containing
        shell metacharacters must arrive as data, not code."""
        ssh = self._ssh_returning([])
        mock_conn.return_value = ssh

        clusterio.find_paths("/a/dir; rm -rf /", "*.zarr", cluster_id="czii", maxdepth=2, entry_type="d")

        command = ssh.exec_command.call_args[0][0]
        assert "'/a/dir; rm -rf /'" in command
        assert "-maxdepth 2" in command
        assert "-type d" in command

    def test_rejects_junk_entry_type(self, mock_conn):
        with pytest.raises(ValueError, match="entry_type"):
            clusterio.find_paths("/a", "*", cluster_id="czii", maxdepth=1, entry_type="x")

    def test_connection_closed(self, mock_conn):
        ssh = self._ssh_returning([])
        mock_conn.return_value = ssh

        clusterio.find_paths("/a", "*", cluster_id="czii", maxdepth=1)

        ssh.close.assert_called_once()
