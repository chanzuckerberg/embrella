"""resolve_dir: the API anyone converting a hardcoded path constant touches."""

import pytest

from stores.models import Cluster, DataKind, PathType
from stores.paths import UnresolvedPlaceholderError, resolve_dir

pytestmark = pytest.mark.django_db


def make_path_type(data_type, overlay_path, cluster=None):
    kind, _ = DataKind.objects.get_or_create(data_type=data_type)
    return PathType.objects.create(data_kind=kind, overlay_path=overlay_path, cluster=cluster)


def make_cluster(cluster_id):
    return Cluster.objects.get_or_create(
        cluster_id=cluster_id,
        defaults={"name": cluster_id.upper(), "http_base_url": f"https://{cluster_id}/", "ssh_hostname": "h"},
    )[0]


class TestResolveDir:
    def test_substitutes_context(self):
        make_path_type("copick_root", "/hpc/{scope}.processing/copick/{msi_session}/{proc_run}/")
        assert (
            resolve_dir("copick_root", scope="krios1", msi_session="24nov10", proc_run="run001")
            == "/hpc/krios1.processing/copick/24nov10/run001/"
        )

    def test_a_template_with_no_placeholders_needs_no_context(self):
        """The conda_env case: per-deployment, but constant once configured."""
        make_path_type("conda_env", "/hpc/software/dataportalenv")
        assert resolve_dir("conda_env") == "/hpc/software/dataportalenv"

    def test_prefers_the_cluster_specific_template(self):
        bruno = make_cluster("bruno")
        make_path_type("conda_env", "/default/env")
        make_path_type("conda_env", "/bruno/env", cluster=bruno)
        assert resolve_dir("conda_env", cluster=bruno) == "/bruno/env"
        assert resolve_dir("conda_env") == "/default/env"

    def test_accepts_a_cluster_id_string(self):
        bruno = make_cluster("bruno")
        make_path_type("conda_env", "/bruno/env", cluster=bruno)
        assert resolve_dir("conda_env", cluster="bruno") == "/bruno/env"


class TestFailsLoudly:
    def test_unknown_kind(self):
        with pytest.raises(PathType.DoesNotExist, match="No PathType for data kind 'nope'"):
            resolve_dir("nope")

    def test_error_names_the_cluster(self):
        with pytest.raises(PathType.DoesNotExist, match="on cluster 'bruno'"):
            resolve_dir("nope", cluster=make_cluster("bruno"))

    def test_missing_context_value_raises_error(self):
        make_path_type("copick_root", "/hpc/copick/{msi_session}/")
        with pytest.raises(UnresolvedPlaceholderError, match=r"still contains \{msi_session\}"):
            resolve_dir("copick_root")

    def test_file_scoped_token_reports_the_real_mistake(self):
        """A directory template carrying its filename half is a different error from a
        missing value, and the message has to say which."""
        make_path_type("frames", "/hpc/{msi_session}/{run}_{tilt}.eer")
        with pytest.raises(UnresolvedPlaceholderError, match="belong in a FilePattern capture group"):
            resolve_dir("frames", msi_session="24nov10")

    def test_strict_can_be_turned_off(self):
        make_path_type("copick_root", "/hpc/copick/{msi_session}/")
        assert resolve_dir("copick_root", strict=False) == "/hpc/copick/{msi_session}/"
