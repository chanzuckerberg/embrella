'use client';

import { Typography } from '@mui/material';
import { BaseFormDialog } from '@app/common/components/Forms/BaseFormDialog';

interface NewSubmissionDialogProps {
  open: boolean;
  onClose: () => void;
}

export function NewSubmissionDialog({ open, onClose }: NewSubmissionDialogProps) {
  return (
    <BaseFormDialog open={open} onClose={onClose} title="New Submission" onSave={onClose} disabled>
      <Typography variant="body1" color="text.secondary">
        Reserve a new deposition ID or continue an existing one - coming soon.
      </Typography>
    </BaseFormDialog>
  );
}
