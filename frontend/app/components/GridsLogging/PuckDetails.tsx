'use client';

import React from 'react';
import { PucksList } from '@app/common/types/gridLogging/puckList';
import { PuckSVG } from './PuckSvg';
import { Card, CardContent, CardHeader, Box, IconButton } from '@mui/material';
import { Button, Icon } from '@czi-sds/components';
import { DJANGO_URL } from '@app/common/constants/api';

interface PuckDetailsProps {
  selectedPuck: PucksList | null;
  onAddGridBox: () => void;
  onSlotSelect: (slotPosition: number) => void;
  _selectedSlot: number | null;
}

export const PuckDetails: React.FC<PuckDetailsProps> = ({
  selectedPuck,
  onAddGridBox,
  onSlotSelect,
  _selectedSlot,
}) => {
  const handleSlotClick = (slotPosition: number) => {
    onSlotSelect(slotPosition);
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
      <CardHeader title={`Puck Details: ${selectedPuck.name}`} />
      <CardContent>
        {/* Display the selected puck SVG */}
        <Box sx={{ display: 'flex', justifyContent: 'center', mb: 4 }}>
          <PuckSVG puck={selectedPuck} size={290} isSelected={true} onSlotClick={handleSlotClick} />
        </Box>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 4 }}>
          <Button
            sdsType="primary"
            sdsStyle="rounded"
            startIcon={<Icon sdsIcon="Plus" sdsSize="s" />}
            onClick={onAddGridBox}
            sx={{ marginTop: '20px' }}
          >
            Add Grid Box
          </Button>
          <IconButton onClick={handleDeletePuck} sx={{ marginTop: '20px' }}>
            <Icon sdsIcon="TrashCan" sdsSize="xl" color="red" />
          </IconButton>
        </Box>

        {/* Display selected slot information */}
        {/* {selectedSlot && (
          <Box sx={{ 
            display: 'flex', 
            justifyContent: 'center', 
            mt: 3,
            mb: 3,
            p: 2,
            backgroundColor: '#e3f2fd',
            borderRadius: 2,
            border: '1px solid #1976d2'
          }}>
            <Typography variant="h6" sx={{ mr: 1 }}>
              Selected Slot:
            </Typography>
            <Chip 
              label={`Slot ${selectedSlot}`}
              color="primary"
              size="large"
              sx={{ 
                fontSize: '1.1rem',
                fontWeight: 'bold',
                height: '32px'
              }}
            />
          </Box>
        )} */}
      </CardContent>
    </Card>
  );
};
