"""deposition_cluster_id reads the admin-set default on the deposition-prep software row."""

import pytest
from processes.models import ProcSoftware

from depositions.services import cluster as cluster_svc
from depositions.services.cluster import deposition_cluster_id


@pytest.mark.django_db
def test_uses_the_prep_software_default_cluster():
    ProcSoftware.objects.filter(processor_class="deposition-prep").delete()
    ProcSoftware.objects.create(name="deposition-prep", processor_class="deposition-prep", default_cluster="bruno")
    assert deposition_cluster_id() == "bruno"


@pytest.mark.django_db
def test_falls_back_to_site_default_when_unset(monkeypatch):
    ProcSoftware.objects.filter(processor_class="deposition-prep").delete()
    ProcSoftware.objects.create(name="deposition-prep", processor_class="deposition-prep", default_cluster="")
    monkeypatch.setattr(cluster_svc, "get_default_cluster_id", lambda: "site-default")
    assert deposition_cluster_id() == "site-default"


@pytest.mark.django_db
def test_inactive_prep_row_is_ignored(monkeypatch):
    ProcSoftware.objects.filter(processor_class="deposition-prep").delete()
    ProcSoftware.objects.create(
        name="deposition-prep", processor_class="deposition-prep", default_cluster="bruno", active=False
    )
    monkeypatch.setattr(cluster_svc, "get_default_cluster_id", lambda: "site-default")
    assert deposition_cluster_id() == "site-default"
