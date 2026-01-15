"""
Tests for common.clusterio module.

Tests SSH connection utilities and authentication helpers.
"""

import base64
from unittest.mock import MagicMock, patch

from common import clusterio


class TestGetAuthForUser:
    """Tests for get_auth_for_user helper function."""

    @patch('common.clusterio.test_ssh_as_user')
    @patch('common.clusterio.get_auth_service_user')
    def test_with_ssh_setup(self, mock_get_service_auth, mock_test_ssh):
        """Test authentication when SSH is already set up."""
        # Mock SSH check returning success
        mock_test_ssh.return_value = {
            "can_connect": True,
            "error": None,
            "cluster_id": "czii",
            "username": "testuser",
        }

        # Mock service user auth
        mock_service_auth = {
            "username": "sumslogs",
            "pkey": MagicMock(),
        }
        mock_get_service_auth.return_value = mock_service_auth

        # Call the function
        auth, error = clusterio.get_auth_for_user("testuser", "czii")

        # Verify result
        assert error is None
        assert auth == mock_service_auth
        mock_test_ssh.assert_called_once_with("testuser", "czii")
        mock_get_service_auth.assert_called_once()

    @patch('common.clusterio.test_ssh_as_user')
    def test_with_password_plain_text(self, mock_test_ssh):
        """Test authentication with plain text password when SSH not set up."""
        # Mock SSH check returning failure
        mock_test_ssh.return_value = {
            "can_connect": False,
            "error": "SSH key not set up",
            "cluster_id": "czii",
            "username": "testuser",
        }

        # Call with plain text password
        auth, error = clusterio.get_auth_for_user("testuser", "czii", password="mypassword")

        # Verify result
        assert error is None
        assert auth == {"username": "testuser", "password": "mypassword"}
        mock_test_ssh.assert_called_once_with("testuser", "czii")

    @patch('common.clusterio.test_ssh_as_user')
    def test_with_password_base64_encoded(self, mock_test_ssh):
        """Test authentication with base64 encoded password when SSH not set up."""
        # Mock SSH check returning failure
        mock_test_ssh.return_value = {
            "can_connect": False,
            "error": "SSH key not set up",
            "cluster_id": "czii",
            "username": "testuser",
        }

        # Encode password
        encoded_password = base64.b64encode(b"mypassword").decode("utf-8")

        # Call with base64 encoded password
        auth, error = clusterio.get_auth_for_user("testuser", "czii", password=encoded_password)

        # Verify result
        assert error is None
        assert auth == {"username": "testuser", "password": "mypassword"}
        mock_test_ssh.assert_called_once_with("testuser", "czii")

    @patch('common.clusterio.test_ssh_as_user')
    def test_without_password_returns_error(self, mock_test_ssh):
        """Test that missing password returns error when SSH not set up."""
        # Mock SSH check returning failure
        mock_test_ssh.return_value = {
            "can_connect": False,
            "error": "SSH key not set up",
            "cluster_id": "czii",
            "username": "testuser",
        }

        # Call without password
        auth, error = clusterio.get_auth_for_user("testuser", "czii")

        # Verify error is returned
        assert auth is None
        assert error is not None
        assert error["error"] == "SSH key not set up for this user"
        assert error["ssh_setup_required"] is True
        assert error["cluster_id"] == "czii"
        assert error["username"] == "testuser"
        mock_test_ssh.assert_called_once_with("testuser", "czii")

    def test_invalid_cluster_id(self):
        """Test that invalid cluster_id returns error."""
        # Call with invalid cluster
        auth, error = clusterio.get_auth_for_user("testuser", "invalid_cluster")

        # Verify error is returned
        assert auth is None
        assert error is not None
        assert "Invalid cluster_id" in error["error"]
        assert error["cluster_id"] == "invalid_cluster"
        assert error["username"] == "testuser"
        assert error["ssh_setup_required"] is False

    @patch('common.clusterio.test_ssh_as_user')
    def test_bruno_cluster(self, mock_test_ssh):
        """Test authentication for bruno cluster."""
        # Mock SSH check returning success
        mock_test_ssh.return_value = {
            "can_connect": True,
            "error": None,
            "cluster_id": "bruno",
            "username": "testuser",
        }

        # Mock service user auth
        with patch('common.clusterio.get_auth_service_user') as mock_get_service_auth:
            mock_service_auth = {
                "username": "sumslogs",
                "pkey": MagicMock(),
            }
            mock_get_service_auth.return_value = mock_service_auth

            # Call the function
            auth, error = clusterio.get_auth_for_user("testuser", "bruno")

            # Verify result
            assert error is None
            assert auth == mock_service_auth
            mock_test_ssh.assert_called_once_with("testuser", "bruno")

    @patch('common.clusterio.test_ssh_as_user')
    def test_password_decode_failure_fallback(self, mock_test_ssh):
        """Test that invalid base64 falls back to plain text password."""
        # Mock SSH check returning failure
        mock_test_ssh.return_value = {
            "can_connect": False,
            "error": "SSH key not set up",
            "cluster_id": "czii",
            "username": "testuser",
        }

        # Use a string that's not valid base64
        invalid_base64 = "not!valid!base64!@#$"

        # Call with invalid base64 (should fall back to plain text)
        auth, error = clusterio.get_auth_for_user("testuser", "czii", password=invalid_base64)

        # Verify result - should use password as-is
        assert error is None
        assert auth == {"username": "testuser", "password": invalid_base64}
