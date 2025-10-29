'use client';

import React from 'react';
import { Box, CircularProgress } from '@mui/material';
import { Button, Dialog, DialogTitle, DialogContent } from '@czi-sds/components';

interface BaseFormDialogProps {
  open: boolean;
  onClose: () => void;
  title: string | React.ReactNode;
  subtitle?: string;
  children: React.ReactNode;
  onSave: () => void;
  isSubmitting?: boolean;
  saveButtonText?: string;
  disabled?: boolean;
}

export const BaseFormDialog: React.FC<BaseFormDialogProps> = ({
  open,
  onClose,
  title,
  subtitle,
  children,
  onSave,
  isSubmitting = false,
  saveButtonText = 'Save',
  disabled = false,
}) => {
  return (
    <Dialog onClose={onClose} open={open} sdsSize="xs">
      <DialogTitle title={title} subtitle={subtitle} onClose={onClose} />
      <DialogContent>
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3, pt: 2, pb: 2, mt: 2 }}>
          {children}

          <Box sx={{ display: 'flex', justifyContent: 'flex-end', gap: 2 }}>
            <Button sdsType="secondary" sdsStyle="rounded" onClick={onClose} disabled={isSubmitting}>
              Cancel
            </Button>
            <Button
              sdsType="primary"
              sdsStyle="rounded"
              onClick={onSave}
              disabled={isSubmitting || disabled}
              startIcon={isSubmitting ? <CircularProgress size={16} /> : undefined}
            >
              {isSubmitting ? 'Saving...' : saveButtonText}
            </Button>
          </Box>
        </Box>
      </DialogContent>
    </Dialog>
  );
};
