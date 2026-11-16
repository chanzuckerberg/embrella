"""Deleting a dataset drops its own Sample, but never a shared grid sample."""

import pytest
from cryo_grids.models import Sample, Specimen

from depositions.models import Dataset, Deposition


def _dataset_with_sample(name_for):
    deposition = Deposition.objects.create(title="Dep")
    dataset = Dataset.objects.create(deposition=deposition, title="DS")
    sample = Sample.objects.create(name=name_for(dataset), sample_type="in_vitro")
    dataset.sample = sample
    dataset.save(update_fields=["sample"])
    return dataset, sample


@pytest.mark.django_db
def test_deleting_dataset_removes_its_owned_sample():
    dataset, sample = _dataset_with_sample(lambda ds: f"deposition-dataset-{ds.id}")
    dataset.delete()
    assert not Sample.objects.filter(pk=sample.pk).exists()


@pytest.mark.django_db
def test_deleting_dataset_keeps_a_shared_grid_sample():
    dataset, sample = _dataset_with_sample(lambda ds: "shared-grid-sample")
    dataset.delete()
    assert Sample.objects.filter(pk=sample.pk).exists()


@pytest.mark.django_db
def test_deleting_dataset_keeps_an_owned_sample_still_linked_to_a_specimen():
    dataset, sample = _dataset_with_sample(lambda ds: f"deposition-dataset-{ds.id}")
    Specimen.objects.create().samples.add(sample)
    dataset.delete()
    assert Sample.objects.filter(pk=sample.pk).exists()


@pytest.mark.django_db
def test_deleting_a_deposition_cascades_and_removes_owned_samples():
    dataset, sample = _dataset_with_sample(lambda ds: f"deposition-dataset-{ds.id}")
    dataset.deposition.delete()
    assert not Sample.objects.filter(pk=sample.pk).exists()
    assert not Dataset.objects.filter(pk=dataset.pk).exists()
