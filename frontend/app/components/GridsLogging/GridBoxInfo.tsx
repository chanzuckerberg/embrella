'use client';

import React from 'react';
import { PucksList } from '@app/common/types/gridLogging/puckList';
import { Card, CardContent, CardHeader, Typography, Box, Chip, IconButton, Divider } from '@mui/material';
import { Button, Icon } from '@czi-sds/components';
import { DJANGO_URL } from '@app/common/constants/api';

interface GridBoxInfoProps {
  selectedPuck: PucksList | null;
  selectedSlot: number | null;
  onClose: () => void;
  onAddGridBox: () => void;
}

export const GridBoxInfo: React.FC<GridBoxInfoProps> = ({ selectedPuck, selectedSlot,  onAddGridBox }) => {
  if (!selectedPuck || !selectedSlot) {
    return null;
  }

  const handleAddGridBox = () => {
    // You can add specific logic for adding grid box to this slot
    onAddGridBox();
  };

  const handleDeleteSlot = () => {
    // Redirect to Django admin for slot management
    const adminUrl = `${DJANGO_URL}/admin/cryo_grids/puck/${selectedPuck.id}/change/`;
    window.open(adminUrl, '_blank');
  };

  return (
    <Card elevation={2} sx={{ maxWidth: 600, width: '100%', mt: 2 }}>
      <CardHeader
        title={`Slot Details: ${selectedPuck.name} - Slot ${selectedSlot}`}
        // action={
        //   <IconButton onClick={onClose} size="small">
        //     <Icon sdsIcon="XMark" sdsSize="s" />
        //   </IconButton>
        // }
      />
      <CardContent>
        {/* Slot Information */}
        <Box sx={{ mb: 3 }}>
          <Typography variant="h6" sx={{ mb: 2, color: 'primary.main' }}>
            Slot Information
          </Typography>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
              <Typography variant="body2" color="text.secondary">
                Puck Name:
              </Typography>
              <Typography variant="body2" fontWeight="medium">
                {selectedPuck.name}
              </Typography>
            </Box>
            <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
              <Typography variant="body2" color="text.secondary">
                Slot Position:
              </Typography>
              <Chip label={`Slot ${selectedSlot}`} color="primary" size="small" />
            </Box>
            <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
              <Typography variant="body2" color="text.secondary">
                Position in Cane:
              </Typography>
              <Typography variant="body2" fontWeight="medium">
                {selectedPuck.position_in_cane}
              </Typography>
            </Box>
            <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
              <Typography variant="body2" color="text.secondary">
                Cane Number:
              </Typography>
              <Typography variant="body2" fontWeight="medium">
                {selectedPuck.cane}
              </Typography>
            </Box>
          </Box>
        </Box>

        <Divider sx={{ my: 2 }} />

        {/* Grid Box Information */}
        <Box sx={{ mb: 3 }}>
          <Typography variant="h6" sx={{ mb: 2, color: 'primary.main' }}>
            Grid Box Information
          </Typography>
          <Box
            sx={{
              p: 2,
              backgroundColor: '#f5f5f5',
              borderRadius: 1,
              textAlign: 'center',
            }}
          >
            <Typography variant="body2" color="text.secondary">
              No grid box assigned to this slot
            </Typography>
          </Box>
        </Box>

        {/* Action Buttons */}
        <Box sx={{ display: 'flex', justifyContent: 'space-between', gap: 2 }}>
          <Button
            sdsType="primary"
            sdsStyle="rounded"
            startIcon={<Icon sdsIcon="Plus" sdsSize="s" />}
            onClick={handleAddGridBox}
            sx={{ flex: 1 }}
          >
            Add Grid Box
          </Button>
          <IconButton
            onClick={handleDeleteSlot}
            sx={{
              border: '1px solid #d32f2f',
              color: '#d32f2f',
              '&:hover': {
                backgroundColor: '#ffebee',
              },
            }}
          >
            <Icon sdsIcon="TrashCan" sdsSize="s" />
          </IconButton>
        </Box>
      </CardContent>
    </Card>
  );
};
