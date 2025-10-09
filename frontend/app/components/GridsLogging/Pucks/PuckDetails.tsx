'use client';

import React, { useState } from 'react';
import { PucksList } from '@app/common/types/gridLogging/puckList';
import { PuckSVG } from './PuckSvg';
import { DeletePuck } from './DeletePuck';
import { Card, CardContent, CardHeader, Box, IconButton, Typography, CircularProgress, Alert } from '@mui/material';
import { Button, Icon } from '@czi-sds/components';
import { DJANGO_URL } from '@app/common/constants/api';
import { useGridLoggingPuckSlots } from '@app/common/hooks/useGridLogging/useGridLoggingPuckSlots';
import styles from '../GridLogging.module.css';
import { UsersList } from '@app/common/types/gridLogging/userList';

interface PuckDetailsProps {
  selectedPuck: PucksList | null;
  onSlotSelect: (slotPosition: number, gridBoxId?: number) => void;
  selectedUser?: UsersList | null;
}

export const PuckDetails: React.FC<PuckDetailsProps> = ({ selectedPuck, onSlotSelect, selectedUser }) => {
  // Fetch puck slots data
  const { slotsData, isSuccess } = useGridLoggingPuckSlots(selectedPuck?.id);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);

  const handleSlotClick = (slotPosition: number) => {
    if (!slotsData) return;

    // Find the slot data for this position
    const slotData = slotsData.slots.find((slot) => slot.position === slotPosition);

    if (slotData) {
      if (slotData.status === 'filled' && slotData.grid_box_id) {
        // Slot is filled, pass the grid box ID to show grid box details
        onSlotSelect(slotPosition, slotData.grid_box_id);
      } else if (slotData.status === 'empty') {
        // Slot is empty, redirect to add grid box function
        handleAddGridBox(slotPosition);
      }
    }
  };

  const handleAddGridBox = (slotPosition?: number) => {
    const prefillParams = new URLSearchParams();
    // Prefill puck with current puck ID
    if (selectedPuck?.id) {
      prefillParams.append('puck', selectedPuck.id.toString());
    }

    // Prefill position_in_puck if provided (when called from handleSlotClick)
    if (slotPosition !== undefined) {
      prefillParams.append('position_in_puck', slotPosition.toString());
    }

    // Add return state parameters
    if (selectedUser?.id) {
      prefillParams.append('return_user_id', selectedUser.id.toString());
    }
    if (selectedPuck?.id) {
      prefillParams.append('return_puck_id', selectedPuck.id.toString());
    }
    if (slotPosition !== undefined) {
      prefillParams.append('return_slot_position', slotPosition.toString());
    }

    const adminUrl = `${DJANGO_URL}/admin/cryo_grids/cryogridbox/add/?${prefillParams.toString()}`;
    window.location.href = adminUrl;
  };

  const handleDeletePuck = () => {
    setDeleteDialogOpen(true);
  };

  if (!selectedPuck) {
    return null;
  }

  return (
    <>
    <Card elevation={2} sx={{ maxWidth: 600, width: '100%' }}>
      <CardHeader
        title={
          <Box className={styles.cardHeader}>
            <Typography variant="h6" component="h2">
              Puck Name: {selectedPuck.name}
            </Typography>
            <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
              <Button
                sdsType="primary"
                sdsStyle="rounded"
                startIcon={<Icon sdsIcon="Plus" sdsSize="s" />}
                onClick={() => handleAddGridBox()}
                size="small"
              >
                Add Grid Box
              </Button>
              <IconButton
                onClick={handleDeletePuck}
                sx={{
                  '&:hover': {
                    backgroundColor: '#ffebee',
                  },
                }}
              >
                <Icon sdsIcon="TrashCan" sdsSize="xl" color="red" />
              </IconButton>
            </Box>
          </Box>
        }
      />

      <CardContent>
        {/* Loading state */}
        {!isSuccess && (
          <Box sx={{ display: 'flex', justifyContent: 'center', mb: 4 }}>
            <CircularProgress size={40} />
          </Box>
        )}

        {/* Error state */}
        {isSuccess && !slotsData && (
          <Box sx={{ display: 'flex', justifyContent: 'center', mb: 4 }}>
            <Alert severity="error">Failed to load puck slots data</Alert>
          </Box>
        )}

        {/* Puck SVG with slots data */}
        {isSuccess && slotsData && (
          <>
            {/* Display the selected puck SVG with slots data */}
            <Box sx={{ display: 'flex', justifyContent: 'center', mb: 4 }}>
              <PuckSVG
                puck={selectedPuck}
                size={290}
                isSelected={true}
                onSlotClick={handleSlotClick}
                slots={slotsData.slots}
              />
            </Box>

            {/* Slot summary information */}
            <Box sx={{ textAlign: 'center', mb: 2, mt: 8 }}>
              <Typography variant="body2" component="div" sx={{ marginLeft: '8px' }}>
                Occupied Slots : {slotsData.slot_summary.filled_count} Filled with grid boxes
              </Typography>
              <Typography variant="body2" component="div" sx={{ marginLeft: '8px' }}>
                Empty Slots: {slotsData.slot_summary.empty_count} Empty
              </Typography>
            </Box>

            {/* Instructions */}
            <Box sx={{ textAlign: 'center' }}>
              <Typography variant="caption" color="text.secondary">
                Click on the individual slots to view/add grid boxes
              </Typography>
            </Box>
          </>
        )}
      </CardContent>
    </Card>

     {/* Delete dialog  */}
    <DeletePuck
      open={deleteDialogOpen}
      onClose={() => setDeleteDialogOpen(false)}
      selectedPuck={selectedPuck}
      slotsData={slotsData || null}
      selectedUser={selectedUser}
    />
    </>
  );
};
