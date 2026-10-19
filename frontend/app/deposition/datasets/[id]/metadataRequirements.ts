import type { DatasetFunding, DatasetSample } from '../../types';
import { BIO_ROWS } from './sections/bioClassificationRows';
import { bioRequirements, isKnownSampleType } from './sections/bioRequirements';

export function datasetMetadataIssues(
  form: {
    title: string;
    description: string;
    sample: DatasetSample;
    assay_label: string;
    assay_ontology_id: string;
    funding: DatasetFunding[];
  },
  authorCount: number | undefined
): string[] {
  const issues: string[] = [];
  if (!form.title.trim()) issues.push('Dataset title is required.');
  if (!form.description.trim()) issues.push('Dataset description is required.');
  if (authorCount === 0) issues.push('Add at least one dataset author, or use the deposition authors.');
  if (!isKnownSampleType(form.sample.sample_type)) issues.push('Choose a sample type on the Dataset step.');
  const requirements = bioRequirements(form.sample.sample_type);
  const sample = form.sample;
  if (requirements.organismRequired || sample.organism_name?.trim() || sample.organism_taxid != null) {
    if (
      !sample.organism_name?.trim() ||
      !Number.isInteger(sample.organism_taxid) ||
      (sample.organism_taxid ?? 0) <= 0
    ) {
      issues.push('Organism name and a positive NCBI Taxonomy ID are required.');
    }
  }
  for (const row of BIO_ROWS) {
    const name = String(sample[row.nameKey] ?? '').trim();
    const id = String(sample[row.idKey] ?? '').trim();
    if ((row.key === requirements.requiredBioField || name || id) && (!name || !id)) {
      issues.push(`${row.label} needs both a name and an ontology ID.`);
    }
  }
  if (
    (form.assay_label.trim() || form.assay_ontology_id.trim()) &&
    (!form.assay_label.trim() || !form.assay_ontology_id.trim())
  ) {
    issues.push('Assay needs both a name and an ontology ID.');
  }
  for (const row of form.funding) {
    if (row.grant_id?.trim() && !row.funding_agency_name?.trim()) {
      issues.push('Add a funding agency name or remove the incomplete funding entry. Grant ID is optional.');
    }
  }
  return issues;
}
