"""The cluster the deposition flow runs on."""

from processes.models import ProcSoftware
from processes.services.cluster_resolver import get_default_cluster_id

DEPOSITION_PROCESSOR = "deposition-prep"


def deposition_cluster_id():
    """Admin-set cluster the deposition flow runs on, or the site default when it's unset."""
    software = ProcSoftware.objects.filter(processor_class=DEPOSITION_PROCESSOR, active=True).first()
    return (software and software.default_cluster) or get_default_cluster_id()
