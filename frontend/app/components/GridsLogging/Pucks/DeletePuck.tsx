'use client';

import React, { useState } from 'react';
import { Box, Typography, CircularProgress, Alert } from '@mui/material';
import { Button, Icon, Dialog, DialogTitle, DialogContent } from '@czi-sds/components';
import { PuckSlotsResponse, PuckList } from '@app/common/types/gridLogging';
import { DJANGO_URL } from '@app/common/constants/api';

interface DeletePuckProps {
  open: boolean;
  onClose: () => void;
  selectedPuck: PuckList | null;
  slotsData: PuckSlotsResponse | null;
  onDeleteSuccess?: () => void;
}

export const DeletePuck: React.FC<DeletePuckProps> = ({ open, onClose, selectedPuck, slotsData, onDeleteSuccess }) => {
  const [isDeleting, setIsDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!selectedPuck || !slotsData) return null;

  const hasFilledGridBoxes = slotsData.slot_summary.filled_count > 0;

  const handleConfirmDelete = async () => {
    if (!selectedPuck) return;

    setIsDeleting(true);
    setError(null);

    try {
      const response = await fetch(`${DJANGO_URL}/api/list/pucks/${selectedPuck.id}/`, {
        method: 'DELETE',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
      });

      const data = await response.json();

      if (response.ok && data.success) {
        if (onDeleteSuccess) {
          onDeleteSuccess();
        }
        // Close the dialog
        onClose();
      } else {
        const errorMessage = data.error || data.detail || 'Failed to delete puck';
        setError(errorMessage);
        setIsDeleting(false);
      }
    } catch (err) {
      setError('An unexpected error occurred while deleting the puck. Please try again.');
      setIsDeleting(false);
    }
  };

  return (
    <Dialog onClose={onClose} open={open} sdsSize="xs">
      <DialogTitle title={`Delete Puck CZII-0${selectedPuck.name}?`} onClose={onClose} />
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
              backgroundColor: hasFilledGridBoxes ? '#ffebee' : '#fff3e0',
              flexShrink: 0,
            }}
          >
            <Icon sdsIcon="ExclamationMarkCircle" sdsSize="l" />
          </Box>
          <Box sx={{ flex: 1 }}>
            {hasFilledGridBoxes ? (
              <>
                <Typography variant="h6" color="error" sx={{ mb: 1 }}>
                  Puck CZII-0{selectedPuck.name} has filled grid boxes!
                </Typography>
                <Typography variant="caption" sx={{ mb: 2 }}>
                  If proceeding with deleting, all grids in the puck will be trashed
                </Typography>
              </>
            ) : (
              <>
                <Typography variant="h6" color="warning.main" sx={{ mb: 1 }}>
                  This puck is empty and can be safely deleted.
                </Typography>
                <Typography variant="caption" sx={{ mb: 2 }}>
                  Would you like to proceed with deleting this puck?
                </Typography>
              </>
            )}
          </Box>
        </Box>

        {!!error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}

        <Box sx={{ display: 'flex', gap: 6, justifyContent: 'flex-end' }}>
          <Button sdsType="secondary" sdsStyle="rounded" onClick={onClose} disabled={isDeleting}>
            No
          </Button>
          <Button
            sdsType="primary"
            sdsStyle="rounded"
            onClick={handleConfirmDelete}
            disabled={isDeleting}
            startIcon={isDeleting ? <CircularProgress size={16} /> : undefined}
          >
            {isDeleting ? 'Deleting...' : 'Yes'}
          </Button>
        </Box>
      </DialogContent>
    </Dialog>
  );
};
