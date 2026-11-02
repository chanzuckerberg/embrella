'use client';

import type { StepDef } from './wizardTypes';
import { DepositionStep } from './steps/DepositionStep';
import { DatasetStep } from './steps/DatasetStep';
import { SourcesStep } from './steps/SourcesStep';
import { AutofillStep } from './steps/AutofillStep';
import { AnnotationsStep } from './steps/AnnotationsStep';
import { SubmitStep } from './steps/SubmitStep';

export const WIZARD_STEPS: StepDef[] = [
  { num: 1, key: 'sources', title: 'Sources', Component: SourcesStep },
  { num: 2, key: 'deposition', title: 'Deposition', Component: DepositionStep },
  { num: 3, key: 'dataset', title: 'Dataset', Component: DatasetStep },
  { num: 4, key: 'autofill', title: 'Auto-fill', Component: AutofillStep },
  { num: 5, key: 'annotations', title: 'Annotations', Component: AnnotationsStep },
  { num: 6, key: 'submit', title: 'Finalize & Submit', Component: SubmitStep },
];
