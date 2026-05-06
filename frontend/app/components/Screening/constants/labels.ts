export type LabelCategory = 'status' | 'microscope' | 'priority';

export const LABEL_CATEGORIES: Record<LabelCategory, readonly string[]> = {
  status: ['TBS', 'TBC', 'TBM'],
  microscope: ['Arctis', 'Hydra1', 'Hydra2', 'Krios1', 'Krios2'],
  priority: ['P1', 'P2', 'P3'],
};

export const LABEL_DISPLAY: Record<string, string> = {
  TBS: 'To Be Screened',
  TBC: 'To Be Collected',
  TBM: 'To Be Milled',
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
