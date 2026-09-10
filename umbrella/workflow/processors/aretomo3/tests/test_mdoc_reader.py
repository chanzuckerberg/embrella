"""
Tests for MDOC magnification reader.
"""

from io import BytesIO
from unittest.mock import MagicMock, patch

from workflow.processors.aretomo3.mdoc_reader import (
    parse_mdoc_magnification,
    read_mdoc_magnification,
)

# Sample MDOC content based on real .scratch/example.mdoc
SAMPLE_MDOC = """\
DataMode = 6
ImageSize = 4096 4096
ImageFile = Position_1.mrc
PixelSpacing = 1.54
Voltage = 300.00

[T = Tomography: KRIOS-9930543 20-Feb-2026 16:58:06]

[T = TiltAxisAngle = -173.94 Binning = 1 SpotSize = 6]

[ZValue = 0]
TiltAngle = -20.02
StagePosition = -453.76 204.76
StageZ = -9.73
Magnification = 81000
Intensity = 0.00
ExposureDose = 1.33
PixelSpacing = 1.54
SpotSize = 6

[ZValue = 1]
TiltAngle = -17.01
Magnification = 81000
"""


class TestParseMdocMagnification:
    def test_parses_magnification_from_real_mdoc(self):
        assert parse_mdoc_magnification(SAMPLE_MDOC) == 81000

    def test_returns_none_when_no_zvalue_0(self):
        content = """\
DataMode = 6
ImageFile = Position_1.mrc

[ZValue = 1]
Magnification = 81000
"""
        assert parse_mdoc_magnification(content) is None

    def test_returns_none_when_no_magnification_in_zvalue_0(self):
        content = """\
[ZValue = 0]
TiltAngle = -20.02
SpotSize = 6

[ZValue = 1]
Magnification = 81000
"""
        assert parse_mdoc_magnification(content) is None

    def test_returns_none_for_empty_content(self):
        assert parse_mdoc_magnification("") is None

    def test_handles_different_magnification_values(self):
        content = """\
[ZValue = 0]
Magnification = 105000

[ZValue = 1]
Magnification = 105000
"""
        assert parse_mdoc_magnification(content) == 105000

    def test_handles_whitespace_variations(self):
        content = """\
[ZValue = 0]
Magnification =  81000
"""
        # Our regex handles extra spaces after =
        assert parse_mdoc_magnification(content) == 81000

    def test_only_reads_zvalue_0(self):
        """Ensure we read from [ZValue = 0], not other sections."""
        content = """\
[ZValue = 0]
TiltAngle = -20.02

[ZValue = 1]
Magnification = 999999
"""
        # No Magnification in ZValue 0, so should return None
        assert parse_mdoc_magnification(content) is None

    def test_header_magnification_ignored(self):
        """Magnification in the header (before any ZValue) should be ignored."""
        content = """\
Magnification = 50000

[ZValue = 0]
Magnification = 81000
"""
        assert parse_mdoc_magnification(content) == 81000


SESSION_DIR = "/hpc/instruments/czii.krios1/OffloadData/26feb20d/"
CLUSTER = "czii"


class TestReadMdocMagnification:
    def _mock_sftp_with_mdoc(self, content: str, filenames=None):
        """Create mock SSH/SFTP that returns given MDOC content."""
        if filenames is None:
            filenames = ["Position_1_1.mdoc"]

        mock_ssh = MagicMock()
        mock_sftp = MagicMock()
        mock_ssh.open_sftp.return_value = mock_sftp
        mock_sftp.listdir.return_value = filenames

        mock_file = BytesIO(content.encode("utf-8"))
        mock_sftp.open.return_value.__enter__ = MagicMock(return_value=mock_file)
        mock_sftp.open.return_value.__exit__ = MagicMock(return_value=False)

        return mock_ssh, mock_sftp

    @patch("workflow.processors.aretomo3.mdoc_reader.get_cluster_ssh_connection")
    def test_success(self, mock_get_conn):
        mock_ssh, mock_sftp = self._mock_sftp_with_mdoc(SAMPLE_MDOC)
        mock_get_conn.return_value = mock_ssh

        result = read_mdoc_magnification(SESSION_DIR, cluster_id=CLUSTER)

        assert result["success"] is True
        assert result["magnification"] == 81000
        assert result["mdoc_file"] == "Position_1_1.mdoc"
        assert result["error"] is None

    @patch("workflow.processors.aretomo3.mdoc_reader.get_cluster_ssh_connection")
    def test_no_mdoc_files(self, mock_get_conn):
        mock_ssh, mock_sftp = self._mock_sftp_with_mdoc("", filenames=["file.mrc", "file.eer"])
        mock_get_conn.return_value = mock_ssh

        result = read_mdoc_magnification(SESSION_DIR, cluster_id=CLUSTER)

        assert result["success"] is False
        assert "No MDOC files" in result["error"]

    @patch("workflow.processors.aretomo3.mdoc_reader.get_cluster_ssh_connection")
    def test_directory_not_found(self, mock_get_conn):
        mock_ssh = MagicMock()
        mock_sftp = MagicMock()
        mock_ssh.open_sftp.return_value = mock_sftp
        mock_sftp.listdir.side_effect = FileNotFoundError()
        mock_get_conn.return_value = mock_ssh

        result = read_mdoc_magnification("/hpc/nowhere/", cluster_id=CLUSTER)

        assert result["success"] is False
        assert "not found" in result["error"]

    @patch("workflow.processors.aretomo3.mdoc_reader.get_cluster_ssh_connection")
    def test_no_magnification_in_mdoc(self, mock_get_conn):
        content = "[ZValue = 0]\nTiltAngle = -20.02\n\n[ZValue = 1]\n"
        mock_ssh, mock_sftp = self._mock_sftp_with_mdoc(content)
        mock_get_conn.return_value = mock_ssh

        result = read_mdoc_magnification(SESSION_DIR, cluster_id=CLUSTER)

        assert result["success"] is False
        assert result["mdoc_file"] == "Position_1_1.mdoc"
        assert "No Magnification field" in result["error"]

    @patch("workflow.processors.aretomo3.mdoc_reader.get_cluster_ssh_connection")
    def test_ssh_connection_error(self, mock_get_conn):
        mock_get_conn.side_effect = Exception("SSH connection failed")

        result = read_mdoc_magnification(SESSION_DIR, cluster_id=CLUSTER)

        assert result["success"] is False
        assert "SSH connection failed" in result["error"]

    @patch("workflow.processors.aretomo3.mdoc_reader.get_cluster_ssh_connection")
    def test_picks_first_mdoc_alphabetically(self, mock_get_conn):
        mock_ssh, mock_sftp = self._mock_sftp_with_mdoc(
            SAMPLE_MDOC,
            filenames=["Position_2.mdoc", "Position_1.mdoc", "other.txt"],
        )
        mock_get_conn.return_value = mock_ssh

        result = read_mdoc_magnification(SESSION_DIR, cluster_id=CLUSTER)

        assert result["success"] is True
        assert result["mdoc_file"] == "Position_1.mdoc"

    @patch("workflow.processors.aretomo3.mdoc_reader.get_cluster_ssh_connection")
    def test_cleanup_on_success(self, mock_get_conn):
        mock_ssh, mock_sftp = self._mock_sftp_with_mdoc(SAMPLE_MDOC)
        mock_get_conn.return_value = mock_ssh

        read_mdoc_magnification(SESSION_DIR, cluster_id=CLUSTER)

        mock_sftp.close.assert_called_once()
        mock_ssh.close.assert_called_once()
