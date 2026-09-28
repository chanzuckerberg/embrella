'use client';

import React from 'react';
import { Alert, Box, CircularProgress, Typography } from '@mui/material';
import { Button, Dialog, DialogContent, DialogTitle, Icon } from '@czi-sds/components';

interface ConfirmDialogProps {
  open: boolean;
  onClose: () => void;
  onConfirm: () => void;
  title: string;
  heading: string;
  body?: React.ReactNode;
  intent?: 'danger' | 'warning';
  confirmText?: string;
  /** Label shown on the confirm button while isSubmitting (e.g. "Deleting…"). Falls back to confirmText. */
  submittingText?: string;
  cancelText?: string;
  isSubmitting?: boolean;
  /** Optional error surfaced above the message (e.g. a failed delete request). */
  error?: string | null;
}

/**
 * Common Confirmation dialog with a circular exclamation icon and a colored heading.
 */
export const ConfirmDialog: React.FC<ConfirmDialogProps> = ({
  open,
  onClose,
  onConfirm,
  title,
  heading,
  body,
  intent = 'danger',
  confirmText = 'Yes',
  submittingText,
  cancelText = 'No',
  isSubmitting = false,
  error,
}) => {
  const isDanger = intent === 'danger';
  const handleKeyDown = (event: React.KeyboardEvent) => {
    if (event.key !== 'Enter' || isSubmitting) return;
    // A focused button already handles Enter; confirming here would double-fire Yes or hijack No/close.
    if ((event.target as HTMLElement).closest('button')) return;
    onConfirm();
  };
  return (
    <Dialog onClose={onClose} open={open} sdsSize="xs" onKeyDown={handleKeyDown}>
      <DialogTitle title={title} onClose={onClose} />
      <DialogContent>
        {error ? (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        ) : null}
        <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 2, mb: 3 }}>
          <Box
            sx={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              width: 48,
              height: 48,
              borderRadius: '50%',
              backgroundColor: isDanger ? '#ffebee' : '#fff3e0',
              flexShrink: 0,
            }}
          >
            <Icon sdsIcon="ExclamationMarkCircle" sdsSize="l" />
          </Box>
          <Box sx={{ flex: 1 }}>
            <Typography variant="h6" color={isDanger ? 'error' : 'warning.main'} sx={{ mb: 1 }}>
              {heading}
            </Typography>
            {body ? <Typography variant="caption">{body}</Typography> : null}
          </Box>
        </Box>

        <Box sx={{ display: 'flex', gap: 6, justifyContent: 'flex-end' }}>
          <Button sdsType="secondary" sdsStyle="outline" onClick={onClose} disabled={isSubmitting}>
            {cancelText}
          </Button>
          <Button
            sdsType="primary"
            sdsStyle="solid"
            onClick={onConfirm}
            disabled={isSubmitting}
            startIcon={isSubmitting ? <CircularProgress size={16} /> : undefined}
          >
            {isSubmitting ? (submittingText ?? confirmText) : confirmText}
          </Button>
        </Box>
      </DialogContent>
    </Dialog>
  );
};
