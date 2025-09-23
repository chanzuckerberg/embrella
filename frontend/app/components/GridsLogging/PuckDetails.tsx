'use client';

import React from 'react';
import { PucksList } from '@app/common/types/gridLogging/puckList';
import { PuckSVG } from './PuckSvg';
import { Card, CardContent, CardHeader, Box, IconButton, Typography, CircularProgress, Alert } from '@mui/material';
import { Button, Icon } from '@czi-sds/components';
import { DJANGO_URL } from '@app/common/constants/api';
import { useGridLoggingPuckSlots } from '@app/common/hooks/useGridLogging/useGridLoggingPuckSlots';
import styles from './GridLogging.module.css';

interface PuckDetailsProps {
  selectedPuck: PucksList | null;
  onSlotSelect: (slotPosition: number, gridBoxId?: number) => void;
  _selectedSlot: number | null;
}

export const PuckDetails: React.FC<PuckDetailsProps> = ({ selectedPuck, onSlotSelect, _selectedSlot }) => {
  // Fetch puck slots data
  const { slotsData, isSuccess } = useGridLoggingPuckSlots(selectedPuck?.id);

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

  const handleAddGridBox = (_slotPosition?: number) => {
    const adminUrl = `${DJANGO_URL}/admin/cryo_grids/cryogridbox/add`;
    window.open(adminUrl, '_blank');
  };

  const handleDeletePuck = () => {
    // Redirect to Django admin puck deletion page
    const adminUrl = `${DJANGO_URL}/admin/cryo_grids/puck/${selectedPuck?.id}/delete/`;
    window.open(adminUrl, '_blank');
  };

  if (!selectedPuck) {
    return null;
  }

  return (
    <Card elevation={2} sx={{ maxWidth: 600, width: '100%' }}>
      <CardHeader
        title={
          <Box className={styles.cardHeader}>
            <Typography variant="h6" component="h2">
              Puck Details: {selectedPuck.name}
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
                Light-colored Slots : {slotsData.slot_summary.filled_count} Filled
              </Typography>
              <Typography variant="body2" component="div" sx={{ marginLeft: '8px' }}>
                Dark-colored Slots: {slotsData.slot_summary.empty_count} Empty
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
  );
};
