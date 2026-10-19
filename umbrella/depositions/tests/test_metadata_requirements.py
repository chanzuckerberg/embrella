"""Sample-dependent preparation rules and optional metadata behavior."""

import pytest

from depositions.services.metadata_requirements import metadata_issues


def complete_metadata(sample_type="in_vitro"):
    return {
        "dataset_title": "Dataset",
        "dataset_description": "Description",
        "authors": [{"name": "Ada Lovelace"}],
        "sample_type": sample_type,
    }


@pytest.mark.parametrize("sample_type", ["in_vitro", "in_silico", "other"])
def test_nonbiological_samples_do_not_require_organism_or_classification(sample_type):
    assert metadata_issues(complete_metadata(sample_type), "Deposition") == []


@pytest.mark.parametrize(
    "sample_type, field, label",
    [
        ("organism", "tissue", "Tissue"),
        ("tissue", "tissue", "Tissue"),
        ("organoid", "tissue", "Tissue"),
        ("primary_cell_culture", "cell_type", "Cell type"),
        ("cell_line", "cell_strain", "Cell strain"),
        ("organelle", "cell_component", "Cell component"),
        ("virus", "cell_component", "Cell component"),
    ],
)
def test_biological_sample_requires_only_its_applicable_classification(sample_type, field, label):
    metadata = complete_metadata(sample_type)
    issues = metadata_issues(metadata, "Deposition")
    assert issues == [
        "Organism name and a positive NCBI Taxonomy ID are required.",
        f"{label} needs both a name and an ontology ID.",
    ]
    metadata["organism"] = {"name": "Example organism", "taxonomy_id": 9606}
    metadata[field] = {"name": "Example classification", "id": "TEST:123"}
    assert metadata_issues(metadata, "Deposition") == []
    metadata[field].pop("name")
    assert metadata_issues(metadata, "Deposition") == [f"{label} needs both a name and an ontology ID."]


def test_required_fields_are_reported_with_screen_labels():
    issues = metadata_issues({}, " ")
    assert issues == [
        "Deposition title is required.",
        "Dataset title is required.",
        "Dataset description is required.",
        "Add at least one dataset author, or use the deposition authors.",
        "Choose a sample type on the Dataset step.",
    ]


def test_email_grant_and_other_optional_sections_are_not_required():
    metadata = complete_metadata()
    metadata["funding"] = [{"funding_agency_name": "NIH"}]
    assert metadata_issues(metadata, "Deposition") == []


@pytest.mark.parametrize(
    "field,label", [("assay", "Assay"), ("disease", "Disease"), ("development_stage", "Development stage")]
)
def test_optional_terms_are_only_checked_when_entered(field, label):
    metadata = complete_metadata()
    assert metadata_issues(metadata, "Deposition") == []
    metadata[field] = {"name": "Partial term"}
    assert metadata_issues(metadata, "Deposition") == [f"{label} needs both a name and an ontology ID."]


def test_invalid_taxonomy_id_is_not_treated_as_complete():
    metadata = complete_metadata("cell_line")
    metadata["organism"] = {"name": "Human", "taxonomy_id": 0}
    metadata["cell_strain"] = {"name": "Example", "id": "CVCL_1234"}
    assert metadata_issues(metadata, "Deposition") == ["Organism name and a positive NCBI Taxonomy ID are required."]
