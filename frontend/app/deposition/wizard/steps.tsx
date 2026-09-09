'use client';

import type { ComponentType } from 'react';
import DescriptionOutlinedIcon from '@mui/icons-material/DescriptionOutlined';
import { Box, Typography } from '@mui/material';

import type { Dataset } from '../types';
import type { StepDef, StepProps } from './wizardTypes';
import { DepositionStep } from './steps/DepositionStep';
import { DatasetStep } from './steps/DatasetStep';
import { SourcesStep } from './steps/SourcesStep';
import { AutofillStep } from './steps/AutofillStep';
import { AnnotationsStep } from './steps/AnnotationsStep';

function placeholder(label: string): ComponentType<StepProps> {
  function PlaceholderStep(_props: StepProps) {
    return (
      <Box
        sx={{
          minHeight: 300,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          textAlign: 'center',
        }}
      >
        <Box
          sx={{
            width: 56,
            height: 56,
            borderRadius: 2,
            bgcolor: 'action.hover',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            mb: 2,
          }}
        >
          <DescriptionOutlinedIcon sx={{ color: 'text.disabled' }} />
        </Box>
        <Typography variant="h6" sx={{ fontWeight: 700, color: 'text.secondary' }}>
          {label} content
        </Typography>
        <Typography variant="body2" sx={{ color: 'text.disabled' }}>
          Each step renders its own form here.
        </Typography>
      </Box>
    );
  }
  return PlaceholderStep;
}

export const WIZARD_STEPS: StepDef[] = [
  { num: 1, key: 'sources', title: 'Sources', Component: SourcesStep },
  { num: 2, key: 'deposition', title: 'Deposition', Component: DepositionStep },
  { num: 3, key: 'dataset', title: 'Dataset', Component: DatasetStep },
  { num: 4, key: 'autofill', title: 'Auto-fill', Component: AutofillStep },
  { num: 5, key: 'annotations', title: 'Annotations', Component: AnnotationsStep },
  { num: 6, key: 'submit', title: 'Finalize & Submit', Component: placeholder('Finalize & Submit') },
];

export function datasetHasAnnotations(dataset: Dataset): boolean {
  return dataset.type !== 'Tomos only';
}

export function isStepSkipped(step: StepDef, dataset: Dataset): boolean {
  if (step.key === 'annotations') return !datasetHasAnnotations(dataset);
  return false;
}
