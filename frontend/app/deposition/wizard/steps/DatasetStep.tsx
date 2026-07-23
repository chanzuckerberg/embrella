'use client';

import type { StepProps } from '../wizardTypes';
import { DatasetForm } from '../../datasets/[id]/DatasetForm';

export function DatasetStep({ dataset, reportSave, readOnly }: StepProps) {
  return <DatasetForm dataset={dataset} reportSave={reportSave} readOnly={readOnly} />;
}
