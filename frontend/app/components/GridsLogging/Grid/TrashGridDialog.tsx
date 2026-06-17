'use client';

import React from 'react';
import { Box, Typography, CircularProgress } from '@mui/material';
import { Button, Icon, Dialog, DialogTitle, DialogContent } from '@czi-sds/components';

interface TrashGridDialogProps {
  open: boolean;
  onClose: () => void;
  onConfirm: () => void;
  isProcessing: boolean;
}

export const TrashGridDialog: React.FC<TrashGridDialogProps> = ({ open, onClose, onConfirm, isProcessing }) => {
  const handleKeyDown = (event: React.KeyboardEvent) => {
    if (event.key === 'Enter' && !isProcessing) {
      onConfirm();
    }
  };

  return (
    <Dialog onClose={onClose} open={open} sdsSize="xs" onKeyDown={handleKeyDown}>
      <DialogTitle title="Trash this grid?" onClose={onClose} />
      <DialogContent>
        <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 2, mb: 3 }}>
          <Box
            sx={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              width: 48,
              height: 48,
              borderRadius: '50%',
              backgroundColor: '#fff3e0',
              flexShrink: 0,
            }}
          >
            <Icon sdsIcon="ExclamationMarkCircle" sdsSize="l" />
          </Box>
          <Box sx={{ flex: 1 }}>
            <Typography variant="h6" color="warning.main" sx={{ mb: 1 }}>
              This action will remove the grid from its current box and puck location.
            </Typography>
            <Typography variant="caption">This cannot be automatically undone.</Typography>
          </Box>
        </Box>

        <Box sx={{ display: 'flex', gap: 6, justifyContent: 'flex-end' }}>
          <Button sdsType="secondary" sdsStyle="outline" onClick={onClose} disabled={isProcessing}>
            No
          </Button>
          <Button
            sdsType="primary"
            sdsStyle="solid"
            onClick={onConfirm}
            disabled={isProcessing}
            startIcon={isProcessing ? <CircularProgress size={16} /> : undefined}
          >
            {isProcessing ? 'Trashing...' : 'Yes'}
          </Button>
        </Box>
      </DialogContent>
    </Dialog>
  );
};
