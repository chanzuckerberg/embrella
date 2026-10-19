"""Tests for the dataset-config YAML serializer."""

import pytest
from cryo_grids.models import Sample
from people.models import Institution, Person

from depositions.models import Dataset, DatasetFunding, Deposition
from depositions.services.config_yaml import build_dataset_metadata, dataset_metadata_patch
from depositions.services.exceptions import SubmissionValidationError


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
@pytest.mark.parametrize("inherit_authors", [True, False])
def test_resolves_ordered_people_without_requiring_email(inherit_authors):
    institution = Institution.objects.create(name="Biohub")
    first = Person.objects.create(
        given_name="Ada", family_name="Lovelace", institution=institution, orcid="0000-0002-1825-0097"
    )
    second = Person.objects.create(given_name="Grace", family_name="Hopper", contact_email="grace@example.org")
    authors = [
        {"author_id": second.pk, "author_list_order": 1},
        {"author_id": first.pk, "is_primary": True, "is_corresponding": True, "author_list_order": 0},
    ]
    dep = Deposition.objects.create(title="Dep", authors_json=authors if inherit_authors else [])
    ds = Dataset.objects.create(
        deposition=dep,
        title="DS",
        is_authors_same_as_deposition=inherit_authors,
        authors_json=[] if inherit_authors else authors,
    )
    assert build_dataset_metadata(ds)["authors"] == [
        {
            "name": "Ada Lovelace",
            "ORCID": first.orcid,
            "affiliation_name": "Biohub",
            "primary_author_status": True,
            "corresponding_author_status": True,
        },
        {"name": "Grace Hopper", "email": "grace@example.org"},
    ]


@pytest.mark.django_db
def test_missing_directory_author_is_an_actionable_error():
    dep = Deposition.objects.create(
        title="Dep",
        authors_json=[{"author_id": 7, "is_primary": True, "author_list_order": 0}],
    )
    ds = Dataset.objects.create(deposition=dep, title="DS", description="d", is_authors_same_as_deposition=True)
    with pytest.raises(SubmissionValidationError, match="Review the authors"):
        build_dataset_metadata(ds)


@pytest.mark.django_db
def test_patch_clears_empty_optional_template_fields():
    dep = Deposition.objects.create(title="Dep")
    ds = Dataset.objects.create(deposition=dep, dataset_id=10002, title="DS", description="Reviewed")
    patch = dataset_metadata_patch(ds)
    assert patch["dataset_title"] == "DS"
    assert patch["dataset_description"] == "Reviewed"
    assert patch["dataset_identifier"] == 10002
    assert patch["funding"] is None
    assert patch["tissue"] is None
    assert patch["disease"] is None
    assert "dates" not in patch


@pytest.mark.django_db
def test_blank_draft_funding_and_biological_rows_are_omitted():
    dep = Deposition.objects.create(title="Dep")
    sample = Sample.objects.create(
        name="blank-optional-fields", sample_type="in_vitro", organism_name=" ", tissue_name=" "
    )
    ds = Dataset.objects.create(deposition=dep, title="DS", sample=sample)
    DatasetFunding.objects.create(dataset=ds, funding_agency_name=" ", grant_id=" ")
    meta = build_dataset_metadata(ds)
    assert "organism" not in meta
    assert "tissue" not in meta
    assert "funding" not in meta
