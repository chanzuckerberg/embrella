"""Deposition staging paths configured by the deployment."""

import pytest

from stores.models import Cluster, DataKind, PathType
from stores.paths import UnresolvedPlaceholderError, resolve_dir
from stores.placeholders import known_placeholders

pytestmark = pytest.mark.django_db


@pytest.fixture
def staging_paths():
    kind, _ = DataKind.objects.get_or_create(data_type="deposition_staging")
    PathType.objects.filter(data_kind=kind).delete()
    default = PathType.objects.create(data_kind=kind, overlay_path="/srv/portal/staging/{deposition_id}/")
    cluster = Cluster.objects.create(cluster_id="staging-test", name="Staging test")
    return kind, default, cluster


def test_deposition_id_is_a_known_placeholder():
    assert "deposition_id" in known_placeholders()


def test_resolves_configured_staging_path(staging_paths):
    assert resolve_dir("deposition_staging", deposition_id=123) == "/srv/portal/staging/123/"


def test_requires_deposition_id(staging_paths):
    with pytest.raises(UnresolvedPlaceholderError):
        resolve_dir("deposition_staging")


def test_cluster_override_leaves_default_unchanged(staging_paths):
    kind, _, cluster = staging_paths
    PathType.objects.create(
        data_kind=kind,
        cluster=cluster,
        overlay_path="/shared/service-user/depositions/{deposition_id}/",
    )
    assert resolve_dir("deposition_staging", cluster=cluster.cluster_id, deposition_id=123) == (
        "/shared/service-user/depositions/123/"
    )
    assert resolve_dir("deposition_staging", deposition_id=123) == "/srv/portal/staging/123/"
