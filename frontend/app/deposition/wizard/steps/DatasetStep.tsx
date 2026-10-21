'use client';

import type { StepProps } from '../wizardTypes';
import { DatasetForm } from '../../datasets/[id]/DatasetForm';

export function DatasetStep({ dataset, reportSave, reportBlocking, readOnly }: StepProps) {
  return <DatasetForm dataset={dataset} reportSave={reportSave} reportBlocking={reportBlocking} readOnly={readOnly} />;
}
