export type Mode = 'new' | 'existing_deposition' | 'reuse_dataset';
export type ExistingTab = 'pick' | 'manual';
export type DatasetChoice = 'new' | 'existing';

export const OPTIONS: { mode: Mode; label: string; desc: string }[] = [
  { mode: 'new', label: 'Reserve new deposition + dataset', desc: 'Create a new deposition and dataset.' },
  {
    mode: 'existing_deposition',
    label: 'Use existing deposition',
    desc: 'Add a new dataset to an existing deposition.',
  },
  { mode: 'reuse_dataset', label: 'Reuse existing dataset', desc: 'Edit and re-push an existing dataset.' },
];

export function depositionLabel(depId?: number | null): string {
  return depId ? `cdp-${depId}` : '(unreserved)';
}

export function datasetLabel(dsId?: number | null): string {
  return dsId ? `ds-${dsId}` : '(unreserved)';
}
