"""Serialize metadata edits with preparation's deposition-level claim."""

from contextlib import contextmanager

from django.db import transaction
from rest_framework.exceptions import APIException

from depositions.models import Dataset, DatasetJob, Deposition, DepositionSession


class MetadataLocked(APIException):
    status_code = 409
    default_code = "metadata_locked"
    default_detail = (
        "Metadata is locked. Wait for running jobs to finish, then use Edit metadata to reset preparation. "
        "Uploaded datasets cannot be edited."
    )


@contextmanager
def metadata_edit(obj, *, deleting=False):
    """Hold preparation's deposition lock through the edit to prevent claim/write races.

    Only new/reset datasets are editable; failed attempts also require reset.
    """
    db = obj._state.db
    target = obj.dataset if isinstance(obj, DepositionSession) else obj
    deposition_id = target.pk if isinstance(target, Deposition) else target.deposition_id
    with transaction.atomic(using=db):
        Deposition.objects.using(db).select_for_update().get(pk=deposition_id)
        jobs = DatasetJob.objects.using(db)
        if isinstance(target, Dataset):
            jobs = jobs.filter(dataset_id=target.pk)
        else:
            jobs = jobs.filter(dataset__deposition_id=deposition_id)
        if jobs.exclude(state="pending").exists():
            if deleting:
                raise MetadataLocked(
                    "Deletion is locked. Wait for running jobs to finish, then reset prepared or failed datasets "
                    "before deleting. Uploaded datasets and their depositions cannot be deleted."
                )
            raise MetadataLocked()
        yield
