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

  const siblingLocked = !!data.datasets?.some(
    (sibling) => sibling.id !== dataset.id && sibling.job && sibling.job.state !== 'pending'
  );

  return (
    <>
      {!readOnly && siblingLocked && (
        <Alert severity="info" sx={{ mb: 3 }}>
          Editing is paused because another dataset in this submission has started preparation.
        </Alert>
      )}
      <DepositionForm deposition={data} reportSave={reportSave} readOnly={readOnly || siblingLocked} />
    </>
  );
}
