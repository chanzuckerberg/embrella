"""Tests for the dataset-config YAML serializer."""

import pytest
import yaml
from cryo_grids.models import Sample

from depositions.models import Dataset, DatasetFunding, Deposition
from depositions.services.config_yaml import build_dataset_metadata, dataset_config_yaml


@pytest.mark.django_db
def test_maps_core_fields():
    dep = Deposition.objects.create(title="Dep")
    sample = Sample.objects.create(
        name="deposition-sample-1",
        sample_type="cell_line",
        organism_name="Homo sapiens",
        organism_taxid=9606,
        tissue_name="brain",
        tissue_id="UBERON:0000955",
        cell_component_name="membrane",
        ontology="GO:0016020",
    )
    ds = Dataset.objects.create(
        deposition=dep,
        dataset_id=10001,
        title="VLP dataset",
        description="desc",
        sample=sample,
        assay_label="cryo-electron tomography",
        assay_ontology_id="EFO:0010961",
        sample_preparation="plunge-frozen",
        dataset_publications="10.1234/abc",
        is_authors_same_as_deposition=False,
        authors_json=[
            {"full_name": "Ada Lovelace", "orcid": "0000-0002-1825-0097", "is_corresponding": True},
        ],
    )
    DatasetFunding.objects.create(dataset=ds, funding_agency_name="NIH", grant_id="R01-1")

    meta = build_dataset_metadata(ds)
    assert meta["dataset_title"] == "VLP dataset"
    assert meta["dataset_description"] == "desc"
    assert meta["dataset_identifier"] == 10001
    assert meta["sample_type"] == "cell_line"
    assert meta["organism"] == {"name": "Homo sapiens", "taxonomy_id": 9606}
    assert meta["tissue"] == {"name": "brain", "id": "UBERON:0000955"}
    # cell_component id maps from Sample.ontology
    assert meta["cell_component"] == {"name": "membrane", "id": "GO:0016020"}
    assert meta["assay"] == {"name": "cryo-electron tomography", "id": "EFO:0010961"}
    assert meta["sample_preparation"] == "plunge-frozen"
    assert meta["cross_references"] == {"publications": "10.1234/abc"}
    assert meta["funding"] == [{"funding_agency_name": "NIH", "grant_id": "R01-1"}]
    assert meta["authors"] == [
        {"name": "Ada Lovelace", "ORCID": "0000-0002-1825-0097", "corresponding_author_status": True},
    ]


@pytest.mark.django_db
def test_omits_empty_optional_fields():
    dep = Deposition.objects.create(title="Dep")
    ds = Dataset.objects.create(deposition=dep, title="Bare", description="")
    meta = build_dataset_metadata(ds)
    assert meta == {"dataset_title": "Bare", "dataset_description": ""}
    for absent in ("organism", "tissue", "assay", "funding", "cross_references", "authors", "dataset_identifier"):
        assert absent not in meta


@pytest.mark.django_db
def test_renders_valid_yaml():
    dep = Deposition.objects.create(title="Dep")
    ds = Dataset.objects.create(deposition=dep, dataset_id=10002, title="DS", description="d")
    text = dataset_config_yaml(ds)
    parsed = yaml.safe_load(text)
    assert parsed["datasets"][0]["metadata"]["dataset_title"] == "DS"
    assert parsed["datasets"][0]["metadata"]["dataset_identifier"] == 10002


@pytest.mark.django_db
def test_people_ref_authors_are_skipped_until_873():
    # author_id refs (no full_name) can't be resolved here — #873 does that.
    dep = Deposition.objects.create(
        title="Dep",
        authors_json=[{"author_id": 7, "is_primary": True, "author_list_order": 0}],
    )
    ds = Dataset.objects.create(deposition=dep, title="DS", description="d", is_authors_same_as_deposition=True)
    assert "authors" not in build_dataset_metadata(ds)
