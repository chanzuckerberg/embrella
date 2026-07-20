import type { ComponentType } from 'react';

import type { Dataset } from '../types';
import type { AutoSaveState } from '../hooks/useDraftAutoSave';

export interface StepProps {
  dataset: Dataset;
  reportSave: (state: AutoSaveState) => void;
  readOnly: boolean;
}

export type StepKey = 'sources' | 'deposition' | 'dataset' | 'autofill' | 'annotations' | 'submit';

export interface StepDef {
  num: number;
  key: StepKey;
  title: string;
  Component: ComponentType<StepProps>;
}
