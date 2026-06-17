'use client';

import React from 'react';
import { Typography, Box, Alert } from '@mui/material';
import { Button, Dialog, DialogContent, DialogTitle, Icon } from '@czi-sds/components';

interface ClipAllGridsDialogProps {
  open: boolean;
  onClose: () => void;
  onConfirm: () => void;
  gridBoxName: string;
  maxGrids: number;
  unclippedCount: number;
  totalGrids: number;
  isProcessing: boolean;
  error?: string | null;
}

export const ClipAllGridsDialog: React.FC<ClipAllGridsDialogProps> = ({
  open,
  onClose,
  onConfirm,
  gridBoxName,
  maxGrids,
  unclippedCount,
  totalGrids,
  isProcessing,
  error,
}) => {
  const alreadyClippedCount = totalGrids - unclippedCount;

  return (
    <Dialog open={open} onClose={onClose} sdsSize="xs">
      <DialogTitle title="Clip All Grids" onClose={onClose} />

      <DialogContent>
        {Boolean(error) && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}

        {unclippedCount === 0 ? (
          <Alert severity="info" sx={{ mb: 2 }}>
            There are no grids to be clipped in this grid box. All grids are already clipped.
          </Alert>
        ) : (
          <Alert severity="warning" sx={{ mb: 2 }}>
            This action will mark all remaining unclipped grids in this grid box as clipped.
          </Alert>
        )}

        <Box sx={{ mb: 2 }}>
          <Typography variant="body1" gutterBottom>
            <strong>Grid Box:</strong> {gridBoxName}
          </Typography>
          <Typography variant="body1" gutterBottom>
            <strong>Max Grids:</strong> {maxGrids}
          </Typography>
          <Typography variant="body1" gutterBottom>
            <strong>Total Grids:</strong> {totalGrids} grid(s)
          </Typography>
          <Typography variant="body1" gutterBottom>
            <strong>Already Clipped:</strong> {alreadyClippedCount} grid(s)
          </Typography>
          <Typography variant="body1" gutterBottom sx={{ color: unclippedCount > 0 ? 'warning.main' : 'success.main' }}>
            <strong>To be Clipped:</strong> {unclippedCount} grid(s)
          </Typography>
        </Box>

        {unclippedCount > 0 && (
          <Typography variant="body2" color="text.secondary">
            Are you sure you want to clip {unclippedCount} grid(s) in this grid box?
          </Typography>
        )}

        <Box sx={{ display: 'flex', gap: 2, justifyContent: 'flex-end', mt: 3 }}>
          <Button onClick={onClose} disabled={isProcessing} sdsType="secondary" sdsStyle="outline">
            {unclippedCount === 0 ? 'Close' : 'Cancel'}
          </Button>
          {unclippedCount > 0 && (
            <Button
              onClick={onConfirm}
              disabled={isProcessing}
              sdsType="primary"
              sdsStyle="solid"
              startIcon={<Icon sdsIcon="Grid" sdsSize="s" />}
            >
              {isProcessing ? 'Clipping...' : `Clip ${unclippedCount} Grid${unclippedCount > 1 ? 's' : ''}`}
            </Button>
          )}
        </Box>
      </DialogContent>
    </Dialog>
  );
};
