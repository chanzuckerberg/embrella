'use client';

import { Alert, Box, CircularProgress } from '@mui/material';

import type { StepProps } from '../wizardTypes';
import { useDeposition } from '../../hooks/useDeposition';
import { DepositionForm } from '../../depositions/DepositionForm';

export function DepositionStep({ dataset, reportSave, readOnly }: StepProps) {
  const { data, isPending, isError } = useDeposition(dataset.deposition ?? null);

  if (isPending) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', py: 6 }}>
        <CircularProgress />
      </Box>
    );
  }
  if (isError || !data) {
    return <Alert severity="error">Could not load the deposition for this dataset.</Alert>;
  }

  return <DepositionForm deposition={data} reportSave={reportSave} readOnly={readOnly || dataset.status !== 'draft'} />;
}
