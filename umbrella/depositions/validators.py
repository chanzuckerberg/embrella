"""Ontology ID formats shared by the deposition API's writable fields."""

from django.core.validators import RegexValidator


def _ontology_id(pattern, example):
    return RegexValidator(
        regex=rf"\A(?:{pattern})\Z",
        message=f"Invalid ontology ID format. Use an ID such as {example}.",
    )


# Keep aligned with BIO_ROWS and ObjectOntologyField in the deposition frontend.
_ANATOMY = r"(?:CL|UBERON|WBbt|ZFA):[0-9]{7}|FBbt:[0-9]{8}"
SAMPLE_ONTOLOGY_VALIDATORS = {
    "tissue_id": _ontology_id(rf"BTO:[0-9]{{7}}|{_ANATOMY}", "UBERON:0000955"),
    "cell_type_id": _ontology_id(_ANATOMY, "CL:0000540"),
    "cell_strain_id": _ontology_id(r"WBStrain[0-9]{8}|NCBITaxon:[0-9]+|CVCL_[A-Z0-9]{4,}|CC-[0-9]{4}", "CVCL_0030"),
    "cell_component_id": _ontology_id(r"GO:[0-9]{7}", "GO:0005737"),
    "development_stage_ontology_id": _ontology_id(
        r"unknown|(?:WBls|UBERON|HsapDv|MmusDv|ZFS):[0-9]{7}|FBdv:[0-9]{8}", "HsapDv:0000087"
    ),
    "disease_ontology_id": _ontology_id(r"(?:MONDO|PATO):[0-9]{7}", "MONDO:0004992"),
}
ASSAY_ONTOLOGY_VALIDATOR = _ontology_id(r"EFO:[0-9]{7}", "EFO:0000269")
ANNOTATION_OBJECT_VALIDATOR = _ontology_id(
    r"(?:GO|UBERON|CDPO):[0-9]{7}|CHEBI:[0-9]+|"
    r"UniProtKB:(?:[OPQ][0-9][A-Z0-9]{3}[0-9]|[A-NR-Z][0-9](?:[A-Z][A-Z0-9]{2}[0-9]){1,2})|"
    r"EMD-[0-9]{4,5}|PDB-[0-9a-zA-Z]{4,8}",
    "GO:0005840 or UniProtKB:P12345",
)
