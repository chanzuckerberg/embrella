"""Preparation requirements matching the Deposition and Dataset wizard screens."""

from cryo_grids.models import SAMPLE_TYPE_CHOICES

ORGANISM_EXEMPT = {"in_vitro", "in_silico", "other"}
# Keep aligned with datasets/[id]/sections/bioRequirements.ts.
REQUIRED_BIO_FIELD = {
    "organism": "tissue",
    "tissue": "tissue",
    "organoid": "tissue",
    "primary_cell_culture": "cell_type",
    "cell_line": "cell_strain",
    "organelle": "cell_component",
    "virus": "cell_component",
}
BIO_LABELS = {
    "tissue": "Tissue",
    "cell_type": "Cell type",
    "cell_strain": "Cell strain",
    "cell_component": "Cell component",
    "development_stage": "Development stage",
    "disease": "Disease",
    "assay": "Assay",
}


def _filled(value):
    return isinstance(value, str) and bool(value.strip())


def dataset_metadata_issues(metadata):
    """Return user-facing issues; optional empty fields never create placeholders."""
    issues = []
    for label, value in (
        ("Dataset title", metadata.get("dataset_title")),
        ("Dataset description", metadata.get("dataset_description")),
    ):
        if not _filled(value):
            issues.append(f"{label} is required.")
    authors = metadata.get("authors") or []
    if not authors:
        issues.append("Add at least one dataset author, or use the deposition authors.")
    else:
        if not any(author.get("primary_author_status") for author in authors):
            issues.append("Choose at least one primary dataset author.")
        if not any(author.get("corresponding_author_status") for author in authors):
            issues.append("Choose at least one corresponding dataset author.")

    sample_type = metadata.get("sample_type")
    if sample_type not in dict(SAMPLE_TYPE_CHOICES):
        issues.append("Choose a sample type on the Dataset step.")

    organism = metadata.get("organism") or {}
    organism_required = bool(sample_type) and sample_type not in ORGANISM_EXEMPT
    if organism_required or organism:
        if (
            not _filled(organism.get("name"))
            or not isinstance(organism.get("taxonomy_id"), int)
            or organism["taxonomy_id"] <= 0
        ):
            issues.append("Organism name and a positive NCBI Taxonomy ID are required.")

    required = REQUIRED_BIO_FIELD.get(sample_type)
    for field, label in BIO_LABELS.items():
        term = metadata.get(field) or {}
        if field == required or term:
            if not _filled(term.get("name")) or not _filled(term.get("id")):
                issues.append(f"{label} needs both a name and an ontology ID.")

    for row in metadata.get("funding") or []:
        if not _filled(row.get("funding_agency_name")):
            issues.append("Add a funding agency name or remove the incomplete funding entry. Grant ID is optional.")
    return issues


def metadata_issues(metadata, deposition_title):
    """Check the full preparation request, including its parent deposition."""
    issues = dataset_metadata_issues(metadata)
    if not _filled(deposition_title):
        issues.insert(0, "Deposition title is required.")
    return issues
