import { mergePreparation } from './preparation';
import type { PreparationSource } from '../../types';

const source: PreparationSource = {
  key: '1:2',
  label: 'session / grid / sample',
  sample_preparation: 'Prepared cells',
  grid_preparation: 'Frozen grid',
  sample: {
    sample_type: 'cell_line',
    organism_name: 'Human',
    organism_taxid: 9606,
    cell_strain_name: 'HeLa',
    cell_strain_id: 'CVCL_0030',
  },
};

it('copies empty preparation and sample fields without mutating the source', () => {
  const result = mergePreparation({ sample: {}, sample_preparation: '', grid_preparation: '' }, source);
  expect(result.sample).toMatchObject(source.sample);
  expect(result.sample_preparation).toBe('Prepared cells');
  expect(result.grid_preparation).toBe('Frozen grid');
  expect(result.sample).not.toBe(source.sample);
});

it('overrides the two prep fields on reuse, but keeps classification blank-fill', () => {
  const previous = {
    sample: { organism_taxid: 10090 },
    sample_preparation: 'Edited prep',
    grid_preparation: 'Edited grid',
  };
  const result = mergePreparation(previous, source);
  // Explicit reuse replaces the prep text...
  expect(result.sample_preparation).toBe('Prepared cells');
  expect(result.grid_preparation).toBe('Frozen grid');
  // ...but classification stays blank-fill: an existing ID is kept and a source name is not paired onto it.
  expect(result.sample.organism_taxid).toBe(10090);
  expect(result.sample).not.toHaveProperty('organism_name');
});

it('clears the prep fields when the selected record has none (re-select overrides stale text)', () => {
  const emptyPrep: PreparationSource = { ...source, sample_preparation: '', grid_preparation: '' };
  const result = mergePreparation(
    { sample: {}, sample_preparation: 'Old prep', grid_preparation: 'Old grid' },
    emptyPrep
  );
  expect(result.sample_preparation).toBe('');
  expect(result.grid_preparation).toBe('');
});

it('does not import classifications from a different sample type', () => {
  const previous = { sample: { sample_type: 'tissue' }, sample_preparation: '', grid_preparation: '' };
  expect(mergePreparation(previous, source).sample).toEqual(previous.sample);
});
