import type { DatasetSample, PreparationSource } from '../../types';
import { BIO_ROWS } from './sections/bioClassificationRows';

export function mergePreparation<
  T extends { sample: DatasetSample; sample_preparation: string; grid_preparation: string },
>(previous: T, source: PreparationSource): T {
  const sample = { ...previous.sample };
  const blank = (value: unknown) => value == null || (typeof value === 'string' && value.trim() === '');
  if (blank(sample.sample_type) || sample.sample_type === source.sample.sample_type) {
    if (blank(sample.sample_type)) sample.sample_type = source.sample.sample_type;
    const pairs: [keyof DatasetSample, keyof DatasetSample][] = [
      ['organism_name', 'organism_taxid'],
      ...BIO_ROWS.map((row): [keyof DatasetSample, keyof DatasetSample] => [row.nameKey, row.idKey]),
    ];
    for (const [nameKey, idKey] of pairs) {
      if (blank(sample[nameKey]) && blank(sample[idKey])) {
        Object.assign(sample, { [nameKey]: source.sample[nameKey], [idKey]: source.sample[idKey] });
      }
    }
  }
  return {
    ...previous,
    sample,
    sample_preparation: source.sample_preparation,
    grid_preparation: source.grid_preparation,
  };
}
