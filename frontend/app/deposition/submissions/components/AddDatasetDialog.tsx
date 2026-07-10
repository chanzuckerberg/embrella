'use client';

import { Typography } from '@mui/material';
import { BaseFormDialog } from '@app/common/components/Forms/BaseFormDialog';

import type { Deposition } from '../../types';

interface AddDatasetDialogProps {
  deposition: Deposition | null; // null = closed
  onClose: () => void;
}

export function AddDatasetDialog({ deposition, onClose }: AddDatasetDialogProps) {
  const label = deposition?.deposition_id ? `cdp-${deposition.deposition_id}` : deposition?.title ?? '';
  return (
    <BaseFormDialog open={deposition !== null} onClose={onClose} title="Add dataset" onSave={onClose} disabled>
      <Typography variant="body1" color="text.secondary">
        Add a dataset to {label} - coming soon.
      </Typography>
    </BaseFormDialog>
  );
}
