"""Save-time ontology formats match the deposition UI, including optional draft fields."""

import pytest

from depositions.serializers import DatasetSampleSerializer, DepositionAnnotationSerializer


@pytest.mark.parametrize(
    "field,valid,invalid",
    [
        # One valid value per accepted prefix (each is a distinct branch of the field's pattern).
        (
            "tissue_id",
            ["BTO:0000142", "CL:0000540", "UBERON:0000955", "WBbt:0003679", "ZFA:0000100", "FBbt:00000001"],
            ["GO:0005737", "UBERON:123"],
        ),
        (
            "cell_type_id",
            ["CL:0000540", "UBERON:0000955", "WBbt:0003679", "ZFA:0000100", "FBbt:00000001"],
            ["BTO:0000142", "CL:123"],
        ),
        ("cell_strain_id", ["WBStrain00000001", "NCBITaxon:562", "CVCL_0030", "CC-0012"], ["CL:0000540", "CVCL_abc"]),
        ("cell_component_id", ["GO:0005737"], ["UBERON:0000955", "go:0005737"]),
        (
            "development_stage_ontology_id",
            [
                "unknown",
                "WBls:0000001",
                "UBERON:0000068",
                "HsapDv:0000087",
                "MmusDv:0000001",
                "ZFS:0000001",
                "FBdv:00000001",
            ],
            ["GO:0005737", "HsapDv:123"],
        ),
        ("disease_ontology_id", ["MONDO:0004992", "PATO:0000461"], ["EFO:0000269", "MONDO:123"]),
    ],
)
def test_sample_ontology_formats(field, valid, invalid):
    for value in valid:
        assert DatasetSampleSerializer(data={field: value}).is_valid()
    for value in invalid:
        serializer = DatasetSampleSerializer(data={field: value})
        assert not serializer.is_valid(), value
        assert field in serializer.errors


def test_blank_sample_ontology_ids_are_allowed():
    # Optional draft fields: blank/whitespace must skip the format check so autosave doesn't 400.
    for value in ("", "   "):
        assert DatasetSampleSerializer(data={"tissue_id": value}).is_valid()


@pytest.mark.parametrize(
    "value",
    ["GO:0005840", "UBERON:0000955", "CHEBI:15377", "UniProtKB:P12345", "CDPO:0000001", "EMD-1234", "PDB-4hhb", ""],
)
def test_annotation_accepts_supported_object_ids(value):
    assert DepositionAnnotationSerializer(data={"object_id": value}, partial=True).is_valid()


@pytest.mark.parametrize(
    # too short, trailing junk, newline (proves full-string anchoring), wrong prefix, embedded in a URL
    "value",
    ["GO:1", "GO:0005840junk", "GO:0005840\nother", "CL:0000540", "https://example.org/GO:0005840"],
)
def test_annotation_rejects_malformed_object_ids(value):
    serializer = DepositionAnnotationSerializer(data={"object_id": value}, partial=True)
    assert not serializer.is_valid()
    assert "object_id" in serializer.errors


@pytest.mark.parametrize("value,valid", [(9606, True), (None, True), (0, False), (-1, False)])
def test_organism_taxonomy_id_must_be_positive_when_set(value, valid):
    assert DatasetSampleSerializer(data={"organism_taxid": value}).is_valid() is valid
