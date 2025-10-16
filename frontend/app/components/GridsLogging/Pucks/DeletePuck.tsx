'use client';

import React, { useState } from 'react';
import { Box, Typography, CircularProgress } from '@mui/material';
import { Button, Icon, Dialog, DialogTitle, DialogContent } from '@czi-sds/components';
import { PucksList } from '@app/common/types/gridLogging/puckList';
import { PuckSlotsResponse } from '@app/common/types/gridLogging/puckList';
import { UsersList } from '@app/common/types/gridLogging/userList';
import { DJANGO_URL } from '@app/common/constants/api';

interface DeletePuckProps {
  open: boolean;
  onClose: () => void;
  selectedPuck: PucksList | null;
  slotsData: PuckSlotsResponse | null;
  selectedUser?: UsersList | null;
}

export const DeletePuck: React.FC<DeletePuckProps> = ({ open, onClose, selectedPuck, slotsData, selectedUser }) => {
  const [isDeleting, setIsDeleting] = useState(false);

  if (!selectedPuck || !slotsData) return null;

  const hasFilledGridBoxes = slotsData.slot_summary.filled_count > 0;

  const handleConfirmDelete = () => {
    if (!selectedPuck) return;

    setIsDeleting(true);
    const prefillParams = new URLSearchParams();

    // Add return state parameters
    if (selectedUser?.id) {
      prefillParams.append('return_user_id', selectedUser.id.toString());
    }

    // Redirect to Django admin puck deletion page
    const adminUrl = `${DJANGO_URL}/admin/cryo_grids/puck/${selectedPuck.id}/delete/?${prefillParams.toString()}`;
    window.location.href = adminUrl;
  };

  return (
    <Dialog onClose={onClose} open={open} sdsSize="xs">
      <DialogTitle title={`Delete Puck ${selectedPuck.name}?`} onClose={onClose} />
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
                  Puck {selectedPuck.name} has filled grid boxes!
                </Typography>
                <Typography variant="caption" sx={{ mb: 2 }}>
                  if proceeding with deleting, all objects in the puck will be trashed
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
