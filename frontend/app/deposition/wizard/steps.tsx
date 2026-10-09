'use client';

import type { Dataset } from '../types';
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

export function datasetHasAnnotations(dataset: Dataset): boolean {
  return dataset.type !== 'Tomos only';
}

export function isStepSkipped(step: StepDef, dataset: Dataset): boolean {
  if (step.key === 'annotations') return !datasetHasAnnotations(dataset);
  return false;
}
