"""Serialize a deposition Dataset to the cryoET portal dataset-config metadata block."""

from people.models import Person

from depositions.services.exceptions import SubmissionValidationError

_ONTOLOGY_FIELDS = [
    ("tissue", "tissue_name", "tissue_id"),
    ("cell_type", "cell_name", "cell_type_id"),
    ("cell_strain", "cell_strain_name", "cell_strain_id"),
    ("cell_component", "cell_component_name", "ontology"),
    ("development_stage", "development_stage_name", "development_stage_ontology_id"),
    ("disease", "disease_name", "disease_ontology_id"),
]

DATASET_METADATA_FIELDS = {
    "dataset_title",
    "dataset_description",
    "dataset_identifier",
    "authors",
    "funding",
    "sample_type",
    "organism",
    "assay",
    "sample_preparation",
    "grid_preparation",
    "other_setup",
    "cross_references",
    *[field[0] for field in _ONTOLOGY_FIELDS],
}


def _name_id(name, oid):
    """A {name, id} block, omitting empty parts."""
    block = {}
    if name and name.strip():
        block["name"] = name.strip()
    if oid and oid.strip():
        block["id"] = oid.strip()
    return block or None


def _map_author(entry, people):
    """Resolve directory references, retaining support for saved inline authors."""
    if not isinstance(entry, dict):
        return None
    email = None
    person_id = entry.get("author_id")
    if person_id is not None:
        person = people.get(person_id)
        if person is None:
            raise SubmissionValidationError(
                "An author is no longer in the people directory. Review the authors before preparing."
            )
        name = str(person)
        orcid = person.orcid
        affiliation = person.institution.name if person.institution else ""
        email = person.contact_email
    else:
        name = (entry.get("full_name") or "").strip()
        orcid = entry.get("orcid")
        affiliation = entry.get("affiliation")
    if not name:
        return None
    author = {"name": name}
    if orcid:
        author["ORCID"] = orcid
    if affiliation:
        author["affiliation_name"] = affiliation
    if email:
        author["email"] = email
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
        if sample.organism_name.strip():
            organism["name"] = sample.organism_name.strip()
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
        agency = f.funding_agency_name.strip()
        grant = f.grant_id.strip()
        if not agency and not grant:
            continue
        row = {"funding_agency_name": agency}
        if grant:
            row["grant_id"] = grant
        funding.append(row)
    if funding:
        meta["funding"] = funding

    source_authors = (
        dataset.deposition.authors_json if dataset.is_authors_same_as_deposition else dataset.authors_json
    ) or []
    people = (
        Person.objects.using(dataset._state.db)
        .select_related("institution")
        .in_bulk(e["author_id"] for e in source_authors if isinstance(e, dict) and e.get("author_id") is not None)
    )
    ordered_authors = sorted(
        ((index, entry) for index, entry in enumerate(source_authors) if isinstance(entry, dict)),
        key=lambda item: item[1]["author_list_order"] if item[1].get("author_list_order") is not None else item[0],
    )
    authors = [a for a in (_map_author(e, people) for _, e in ordered_authors) if a]
    if authors:
        meta["authors"] = authors

    return meta


def dataset_metadata_patch(dataset):
    """Nulls remove empty wizard-owned fields from the tool's generated template."""
    return {**dict.fromkeys(DATASET_METADATA_FIELDS), **build_dataset_metadata(dataset)}
