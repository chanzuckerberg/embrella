"""Serialize a deposition Dataset to the cryoET portal dataset-config metadata block."""

import yaml

_ONTOLOGY_FIELDS = [
    ("tissue", "tissue_name", "tissue_id"),
    ("cell_type", "cell_name", "cell_type_id"),
    ("cell_strain", "cell_strain_name", "cell_strain_id"),
    ("cell_component", "cell_component_name", "ontology"),
    ("development_stage", "development_stage_name", "development_stage_ontology_id"),
    ("disease", "disease_name", "disease_ontology_id"),
]


def _name_id(name, oid):
    """A {name, id} block, omitting empty parts."""
    block = {}
    if name:
        block["name"] = name
    if oid:
        block["id"] = oid
    return block or None


def _map_author(entry):
    """Map a authors to the portal author shape."""
    if not isinstance(entry, dict):
        return None
    name = (entry.get("full_name") or "").strip()
    if not name:
        return None
    author = {"name": name}
    if entry.get("orcid"):
        author["ORCID"] = entry["orcid"]
    if entry.get("affiliation"):
        author["affiliation_name"] = entry["affiliation"]
    if entry.get("is_primary"):
        author["primary_author_status"] = True
    if entry.get("is_corresponding"):
        author["corresponding_author_status"] = True
    return author


def build_dataset_metadata(dataset) -> dict:
    """Build the portal `metadata` block for one Dataset."""
    meta = {
        "dataset_title": dataset.title or "",
        "dataset_description": dataset.description or "",
    }
    if dataset.dataset_id is not None:
        meta["dataset_identifier"] = dataset.dataset_id

    sample = dataset.sample
    if sample is not None:
        if sample.sample_type:
            meta["sample_type"] = sample.sample_type
        organism = {}
        if sample.organism_name:
            organism["name"] = sample.organism_name
        if sample.organism_taxid is not None:
            organism["taxonomy_id"] = sample.organism_taxid
        if organism:
            meta["organism"] = organism
        for key, name_attr, id_attr in _ONTOLOGY_FIELDS:
            block = _name_id(getattr(sample, name_attr, "") or "", getattr(sample, id_attr, "") or "")
            if block:
                meta[key] = block

    assay = _name_id(dataset.assay_label, dataset.assay_ontology_id)
    if assay:
        meta["assay"] = assay

    if dataset.sample_preparation:
        meta["sample_preparation"] = dataset.sample_preparation
    if dataset.grid_preparation:
        meta["grid_preparation"] = dataset.grid_preparation
    if dataset.other_setup:
        meta["other_setup"] = dataset.other_setup

    cross = {}
    if dataset.dataset_publications:
        cross["publications"] = dataset.dataset_publications
    if dataset.related_database_entries:
        cross["related_database_entries"] = dataset.related_database_entries
    if cross:
        meta["cross_references"] = cross

    funding = []
    for f in dataset.funding.all():
        row = {"funding_agency_name": f.funding_agency_name}
        if f.grant_id:
            row["grant_id"] = f.grant_id
        funding.append(row)
    if funding:
        meta["funding"] = funding

    source_authors = (
        dataset.deposition.authors_json if dataset.is_authors_same_as_deposition else dataset.authors_json
    ) or []
    authors = [a for a in (_map_author(e) for e in source_authors) if a]
    if authors:
        meta["authors"] = authors

    return meta


def dataset_config_yaml(dataset) -> str:
    """Render the dataset-config YAML."""
    config = {"datasets": [{"metadata": build_dataset_metadata(dataset)}]}
    return yaml.safe_dump(config, sort_keys=False, allow_unicode=True, default_flow_style=False)
