'use client';

import React, { useState } from 'react';
import { Box, Typography, CircularProgress } from '@mui/material';
import { Button, Icon, Dialog, DialogTitle, DialogContent } from '@czi-sds/components';
import { PucksList } from '@app/common/types/gridLogging/puckList';
import { UsersList } from '@app/common/types/gridLogging/userList';
import { GridBoxDetailResponse } from '@app/common/types/gridLogging/gridBoxDetails';
import { DJANGO_URL } from '@app/common/constants/api';

interface DeleteGridBoxProps {
  open: boolean;
  onClose: () => void;
  selectedPuck: PucksList | null;
  selectedSlot: number | null;
  gridBoxData: GridBoxDetailResponse | null;
  selectedUser?: UsersList | null;
}

export const DeleteGridBox: React.FC<DeleteGridBoxProps> = ({
  open,
  onClose,
  selectedPuck,
  selectedSlot,
  gridBoxData,
  selectedUser
}) => {
  const [isDeleting, setIsDeleting] = useState(false);
  let gridBoxId= gridBoxData?.grid_box?.grid_box_id;

  if (!selectedPuck || !gridBoxId) return null;

  // Get the grid box name from gridBoxData
  const gridBoxName = gridBoxData?.grid_box?.name || `Grid Box at position ${selectedSlot}`;
  
  // Check if this grid box has any grids
  const hasGrids = gridBoxData?.grid_box?.positions?.some(position => position.occupied) || false;

  const handleConfirmDelete = () => {
    if (!selectedPuck) return;
    
    setIsDeleting(true);
    const prefillParams = new URLSearchParams();

    if (selectedUser?.id) {
      prefillParams.append('return_user_id', selectedUser.id.toString());
    }
    if (selectedPuck?.id) {
      prefillParams.append('return_puck_id', selectedPuck.id.toString());
    }

    const adminUrl = `${DJANGO_URL}/admin/cryo_grids/cryogridbox/${gridBoxId}/delete/?${prefillParams.toString()}`;
    window.location.href = adminUrl;
  };

  return (
    <Dialog 
      onClose={onClose} 
      open={open} 
      sdsSize="xs"
    >
      <DialogTitle 
        title={`Delete Grid Box ${gridBoxName}?`} 
        onClose={onClose} 
      />
      <DialogContent>
        <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 2, mb: 3 }}>
          <Box sx={{ 
            display: 'flex', 
            alignItems: 'center', 
            justifyContent: 'center',
            width: 48,
            height: 48,
            borderRadius: '50%',
            backgroundColor: hasGrids ? '#ffebee' : '#fff3e0',
            flexShrink: 0
          }}>
            <Icon 
              sdsIcon="ExclamationMarkCircle" 
              sdsSize="l" 
            />
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
          <Button
            sdsType="secondary"
            sdsStyle="rounded"
            onClick={onClose}
            disabled={isDeleting}
          >
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