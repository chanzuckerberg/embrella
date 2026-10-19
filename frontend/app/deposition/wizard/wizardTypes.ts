import type { ComponentType } from 'react';

import type { Dataset } from '../types';
import type { AutoSaveState } from '../hooks/useDraftAutoSave';

export interface StepProps {
  dataset: Dataset;
  reportSave: (state: AutoSaveState) => void;
  /** Report how many required fields are still blocking. */
  reportBlocking?: (count: number) => void;
  readOnly: boolean;
  manualAutofillSessions?: Set<string>;
  onManualAutofillEntry?: (sessionKey: string) => void;
}

export type StepKey = 'sources' | 'deposition' | 'dataset' | 'autofill' | 'annotations' | 'submit';

export interface StepDef {
  num: number;
  key: StepKey;
  title: string;
  Component: ComponentType<StepProps>;
}
