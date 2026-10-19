import { datasetMetadataIssues } from './metadataRequirements';

const form = {
  title: 'Dataset',
  description: 'Description',
  sample: { sample_type: 'in_vitro' },
  assay_label: '',
  assay_ontology_id: '',
  funding: [],
};

it.each(['in_vitro', 'in_silico', 'other'])(
  'allows %s without organism, email, funding or biological terms',
  (sampleType) => {
    expect(datasetMetadataIssues({ ...form, sample: { sample_type: sampleType } }, 1)).toEqual([]);
  }
);

it.each([
  ['organism', 'tissue_name', 'tissue_id', 'Tissue'],
  ['tissue', 'tissue_name', 'tissue_id', 'Tissue'],
  ['organoid', 'tissue_name', 'tissue_id', 'Tissue'],
  ['primary_cell_culture', 'cell_name', 'cell_type_id', 'Cell type'],
  ['cell_line', 'cell_strain_name', 'cell_strain_id', 'Cell strain'],
  ['organelle', 'cell_component_name', 'ontology', 'Cell component'],
  ['virus', 'cell_component_name', 'ontology', 'Cell component'],
])('requires organism and the applicable term for %s', (sampleType, nameKey, idKey, label) => {
  expect(datasetMetadataIssues({ ...form, sample: { sample_type: sampleType } }, 1)).toEqual([
    'Organism name and a positive NCBI Taxonomy ID are required.',
    `${label} needs both a name and an ontology ID.`,
  ]);
  expect(
    datasetMetadataIssues(
      {
        ...form,
        sample: {
          sample_type: sampleType,
          organism_name: 'Example organism',
          organism_taxid: 9606,
          [nameKey]: 'Example term',
          [idKey]: 'TEST:123',
        },
      },
      1
    )
  ).toEqual([]);
});

it('requires effective authors and reports human field names', () => {
  expect(datasetMetadataIssues({ ...form, title: ' ', description: '' }, 0)).toEqual([
    'Dataset title is required.',
    'Dataset description is required.',
    'Add at least one dataset author, or use the deposition authors.',
  ]);
});

it('allows no funding, blank draft rows and an agency without a grant ID', () => {
  expect(datasetMetadataIssues({ ...form, funding: [{ funding_agency_name: '', grant_id: '' }] }, 1)).toEqual([]);
  expect(datasetMetadataIssues({ ...form, funding: [{ funding_agency_name: 'NIH', grant_id: '' }] }, 1)).toEqual([]);
});

it('requires both parts of optional terms only when entered', () => {
  expect(datasetMetadataIssues({ ...form, assay_label: 'Microscopy' }, 1)).toEqual([
    'Assay needs both a name and an ontology ID.',
  ]);
  expect(
    datasetMetadataIssues({ ...form, sample: { sample_type: 'in_vitro', disease_name: 'Partial disease' } }, 1)
  ).toEqual(['Disease needs both a name and an ontology ID.']);
});
