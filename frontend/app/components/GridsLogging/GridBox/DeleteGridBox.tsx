'use client';

import React, { useState } from 'react';
import { Box, Typography, CircularProgress } from '@mui/material';
import { Button, Icon, Dialog, DialogTitle, DialogContent } from '@czi-sds/components';
import { PuckList } from '@app/common/types/gridLogging';
import { GridBoxDetailResponse } from '@app/common/types/gridLogging';
import { DJANGO_URL } from '@app/common/constants/api';

interface DeleteGridBoxProps {
  open: boolean;
  onClose: () => void;
  selectedPuck: PuckList | null;
  selectedSlot: number | null;
  gridBoxData: GridBoxDetailResponse | null;
  onGridBoxDeleted: () => void;
}

export const DeleteGridBox: React.FC<DeleteGridBoxProps> = ({
  open,
  onClose,
  selectedPuck,
  selectedSlot,
  gridBoxData,
  onGridBoxDeleted,
}) => {
  const [isDeleting, setIsDeleting] = useState(false);
  const gridBoxId = gridBoxData?.grid_box?.grid_box_id;

  if (!selectedPuck || !gridBoxId) return null;

  // Get the grid box name from gridBoxData
  const gridBoxName = gridBoxData?.grid_box?.name || `Grid Box at position ${selectedSlot}`;

  // Check if this grid box has any grids
  const hasGrids = gridBoxData?.grid_box?.positions?.some((position) => position.occupied) || false;

  const handleConfirmDelete = async () => {
    if (!selectedPuck || !gridBoxId) return;
    setIsDeleting(true);

    try {
      const response = await fetch(`${DJANGO_URL}/api/list/pucks/grid-box/${gridBoxId}/`, {
        method: 'DELETE',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
      });

      const data = await response.json();

      if (response.ok && data.success) {
        if (onGridBoxDeleted) {
          onGridBoxDeleted();
        }
        // Close the dialog
        onClose();
      } else {
        const errorMessage = data.error || data.detail || 'Failed to delete grid box';
        console.error('Failed to delete grid box:', errorMessage);
        setIsDeleting(false);
      }
    } catch (error) {
      console.error('Error deleting grid box:', error);
      setIsDeleting(false);
    }
  };

  return (
    <Dialog onClose={onClose} open={open} sdsSize="xs">
      <DialogTitle title={`Delete Grid Box ${gridBoxName}?`} onClose={onClose} />
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
              backgroundColor: hasGrids ? '#ffebee' : '#fff3e0',
              flexShrink: 0,
            }}
          >
            <Icon sdsIcon="ExclamationMarkCircle" sdsSize="l" />
          </Box>
          <Box sx={{ flex: 1 }}>
            {hasGrids ? (
              <>
                <Typography variant="h6" color="error" sx={{ mb: 1 }}>
                  Gridbox {selectedSlot} has filled grids!
                </Typography>
                <Typography variant="caption" sx={{ mb: 2 }}>
                  if proceeding with deleting, all grids in the gridbox will be trashed
                </Typography>
              </>
            ) : (
              <>
                <Typography variant="h6" color="warning.main" sx={{ mb: 1 }}>
                  This Gridbox is empty and can be safely deleted.
                </Typography>
                <Typography variant="caption" sx={{ mb: 2 }}>
                  Would you like to proceed with deleting this gridbox?
                </Typography>
              </>
            )}
          </Box>
        </Box>

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
