import type { DatasetSample } from '../../../types';
import { BIO_ROWS } from './bioClassificationRows';

export type RequiredBioField = 'tissue' | 'cell_type' | 'cell_strain' | 'cell_component' | null;

const ORGANISM_EXEMPT = new Set(['in_vitro', 'in_silico', 'other']);

const REQUIRED_BIO_FIELD: Record<string, Exclude<RequiredBioField, null>> = {
  organism: 'tissue',
  tissue: 'tissue',
  organoid: 'tissue',
  primary_cell_culture: 'cell_type',
  cell_line: 'cell_strain',
  organelle: 'cell_component',
  virus: 'cell_component',
};

export interface BioRequirements {
  organismRequired: boolean;
  requiredBioField: RequiredBioField;
}

export function bioRequirements(sampleType?: string): BioRequirements {
  const t = sampleType ?? '';
  return {
    organismRequired: t !== '' && !ORGANISM_EXEMPT.has(t),
    requiredBioField: REQUIRED_BIO_FIELD[t] ?? null,
  };
}

export function isRequiredBioFieldMet(sample: DatasetSample, req: BioRequirements): boolean {
  if (!req.requiredBioField) return true;
  const row = BIO_ROWS.find((r) => r.key === req.requiredBioField);
  if (!row) return true;
  const name = (sample[row.nameKey] as string) ?? '';
  const id = (sample[row.idKey] as string) ?? '';
  return name.trim() !== '' && id.trim() !== '';
}
