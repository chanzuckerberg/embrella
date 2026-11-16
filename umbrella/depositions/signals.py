"""Clean up a dataset's own Sample when the dataset is deleted, so they don't pile up."""

from django.db.models.signals import post_delete
from django.dispatch import receiver

from depositions.models import Dataset


@receiver(post_delete, sender=Dataset)
def _delete_owned_sample(sender, instance, **kwargs):
    """Drop the per-dataset Sample (name="deposition-dataset-<id>"); leave shared grid samples alone.
    Runs for direct deletes and for the cascade when a deposition is deleted."""
    sample = instance.sample
    if sample is None or sample.name != instance.owned_sample_name():
        return
    # Only drop it once nothing else points at it — another dataset (PROTECT) or a specimen.
    if not sample.datasets.exists() and not sample.specimen_set.exists():
        sample.delete()
