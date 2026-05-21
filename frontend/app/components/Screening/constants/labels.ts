export type LabelCategory = 'status' | 'microscope' | 'priority';

export const LABEL_CATEGORIES: Record<LabelCategory, readonly string[]> = {
  status: ['TBS', 'TBC', 'TBM', 'To Be Screened', 'To Be Collected', 'To Be Milled'],
  microscope: ['Arctis', 'Hydra1', 'Hydra2', 'Krios1', 'Krios2'],
  priority: ['P1', 'P2', 'P3'],
};

/**
 * Subset of LABEL_CATEGORIES offered in the Status column's pick-from-dropdown.
 * Status accepts both short (TBS/TBC/TBM) and long ("To Be Screened" etc.) forms
 * for detection, but only the long form is offered to new selections.
 */
export const LABEL_PICKABLE: Record<LabelCategory, readonly string[]> = {
  status: ['To Be Screened', 'To Be Collected', 'To Be Milled'],
  microscope: ['Arctis', 'Hydra1', 'Hydra2', 'Krios1', 'Krios2'],
  priority: ['P1', 'P2', 'P3'],
};

export const LABEL_DISPLAY: Record<string, string> = {
  TBS: 'To Be Screened',
  TBC: 'To Be Collected',
  TBM: 'To Be Milled',
  'To Be Screened': 'To Be Screened',
  'To Be Collected': 'To Be Collected',
  'To Be Milled': 'To Be Milled',
  Arctis: 'Arctis',
  Hydra1: 'Hydra 1',
  Hydra2: 'Hydra 2',
  Krios1: 'Krios 1',
  Krios2: 'Krios 2',
  P1: 'P1',
  P2: 'P2',
  P3: 'P3',
};

export const labelDisplayName = (name: string): string => LABEL_DISPLAY[name] ?? name;
