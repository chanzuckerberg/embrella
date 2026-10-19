'use client';

import { Alert } from '@mui/material';
import type { Dataset } from '../types';

export function ReadOnlyNotice({ dataset }: { dataset: Dataset }) {
  let message = 'This dataset is read-only.';
  if (dataset.is_owner === false) message = 'Only the submission owner can edit this dataset.';
  else if (dataset.status === 'pushed') message = 'Uploaded datasets can’t be edited.';
  else if (dataset.status === 'syncing') message = 'Editing is paused during preparation and upload.';
  return (
    <Alert severity="info" sx={{ mb: 3 }}>
      {message}
    </Alert>
  );
}
