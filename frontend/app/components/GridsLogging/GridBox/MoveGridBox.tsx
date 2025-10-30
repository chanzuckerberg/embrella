'use client';

import React, { useState, useEffect, useMemo } from 'react';
import { Box, TextField, MenuItem, Tooltip, Typography } from '@mui/material';
import { Icon } from '@czi-sds/components';
import { PucksList } from '@app/common/types/gridLogging/puckList';
import { GridBoxDetailResponse } from '@app/common/types/gridLogging/gridBoxDetails';
import { UsersList } from '@app/common/types/gridLogging/userList';
import { useGridLoggingPucksByCane } from '@app/common/hooks/useGridLogging/useGridLoggingPuckList';
import { useGridLoggingPuckSlots } from '@app/common/hooks/useGridLogging/useGridLoggingPuckSlots';
import { useGridLoggingChoices } from '@app/common/hooks/useGridLogging/useGridLoggingChoices';
import { BaseFormDialog } from '@app/common/components/Forms/BaseFormDialog';

interface MoveGridBoxProps {
  open: boolean;
  onClose: () => void;
  currentPuck: PucksList | null;
  currentSlot: number | null;
  gridBoxData: GridBoxDetailResponse | null;
  selectedUser?: UsersList | null;
}

export const MoveGridBox: React.FC<MoveGridBoxProps> = ({
  open,
  onClose,
  currentPuck,
  currentSlot,
  gridBoxData,
  selectedUser,
}) => {
  const [formData, setFormData] = useState({
    destinationCane: '',
    destinationPuck: '',
    destinationPosition: '',
  });
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Fetch choices (for cane colors)
  const { choices, isSuccess: choicesLoaded } = useGridLoggingChoices();

  // Fetch pucks for selected cane (dynamically)
  const { pucks: pucksInCane, isSuccess: pucksLoaded } = useGridLoggingPucksByCane(
    formData.destinationCane ? Number(formData.destinationCane) : undefined
  );

  // Fetch available positions for selected puck
  const { slotsData, isSuccess: slotsLoaded } = useGridLoggingPuckSlots(
    formData.destinationPuck ? Number(formData.destinationPuck) : undefined
  );

  // Reset form when dialog opens
  useEffect(() => {
    if (open) {
      setFormData({
        destinationCane: '',
        destinationPuck: '',
        destinationPosition: '',
      });
    }
  }, [open]);

  // Get available positions (empty slots only) from the puck slots API
  const availablePositions = useMemo(() => {
    if (!slotsData?.slots) return [];
    return slotsData.slots.filter((slot) => slot.status === 'empty');
  }, [slotsData]);

  const handleInputChange = (field: string, value: string) => {
    setFormData((prev) => ({
      ...prev,
      [field]: value,
    }));

    // Reset downstream selections when parent changes
    if (field === 'destinationCane') {
      setFormData((prev) => ({
        ...prev,
        destinationPuck: '',
        destinationPosition: '',
      }));
    } else if (field === 'destinationPuck') {
      setFormData((prev) => ({
        ...prev,
        destinationPosition: '',
      }));
    }
  };

  const handleMove = () => {
    if (!formData.destinationCane || !formData.destinationPuck || !formData.destinationPosition) {
      alert('Please select cane, puck, and position');
      return;
    }

    setIsSubmitting(true);

    const selectedPuck = pucksInCane?.pucks?.find((p) => p.id.toString() === formData.destinationPuck);

    console.log('Moving grid box:', {
      from: {
        puck: currentPuck?.name,
        puck_id: currentPuck?.id,
        position: currentSlot,
      },
      to: {
        cane_id: formData.destinationCane,
        puck: selectedPuck?.name,
        puck_id: formData.destinationPuck,
        position: formData.destinationPosition,
      },
      gridBox: {
        name: gridBoxData?.grid_box?.name,
        id: gridBoxData?.grid_box?.grid_box_id,
      },
    });
  };

  const isFormValid = formData.destinationCane && formData.destinationPuck && formData.destinationPosition;

  // Tooltip content showing current location
  const currentLocationTooltip = (
    <Box sx={{ p: 1 }}>
      <Typography variant="body2" sx={{ fontWeight: 'bold', mb: 0.5 }}>
        Current Location:
      </Typography>
      <Typography variant="caption" display="block">
        Grid Box: {gridBoxData?.grid_box?.name || 'N/A'}
      </Typography>
      <Typography variant="caption" display="block">
        Puck: {currentPuck?.name || 'N/A'}
      </Typography>
      <Typography variant="caption" display="block">
        Position: {currentSlot || 'N/A'}
      </Typography>
    </Box>
  );

  return (
    <BaseFormDialog
      open={open}
      onClose={onClose}
      title={
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          Move Grid Box
          <Tooltip title={currentLocationTooltip} arrow placement="right">
            <Box sx={{ display: 'flex', alignItems: 'center', cursor: 'help' }}>
              <Icon sdsIcon="InfoCircle" sdsSize="s" />
            </Box>
          </Tooltip>
        </Box>
      }
      subtitle={selectedUser?.full_name || ''}
      onSave={handleMove}
      isSubmitting={isSubmitting}
      saveButtonText="Move"
      disabled={!isFormValid || !choicesLoaded}
    >
      <TextField
        select
        required
        fullWidth
        label="Cane"
        value={formData.destinationCane}
        onChange={(e) => handleInputChange('destinationCane', e.target.value)}
      >
        {!choicesLoaded && <MenuItem value="">Loading canes...</MenuItem>}
        {choicesLoaded && (!choices?.cane_colors || choices.cane_colors.length === 0) && (
          <MenuItem value="">No canes available</MenuItem>
        )}
        {choices?.cane_colors?.map((cane, index) => (
          <MenuItem key={cane.value} value={(index + 1).toString()}>
            {cane.label} Cane
          </MenuItem>
        ))}
      </TextField>

      <TextField
        select
        required
        fullWidth
        label="Puck"
        value={formData.destinationPuck}
        onChange={(e) => handleInputChange('destinationPuck', e.target.value)}
        disabled={!formData.destinationCane}
      >
        {!formData.destinationCane && <MenuItem value="">Select a cane first</MenuItem>}
        {formData.destinationCane && !pucksLoaded && <MenuItem value="">Loading pucks...</MenuItem>}
        {formData.destinationCane && pucksLoaded && (!pucksInCane?.pucks || pucksInCane.pucks.length === 0) && (
          <MenuItem value="">No pucks in this cane</MenuItem>
        )}
        {pucksInCane?.pucks?.map((puck) => (
          <MenuItem key={puck.id} value={puck.id.toString()}>
            {puck.name} - Pos {puck.position_in_cane} ({puck.color_display})
          </MenuItem>
        ))}
      </TextField>

      <TextField
        select
        required
        fullWidth
        label="Slot"
        value={formData.destinationPosition}
        onChange={(e) => handleInputChange('destinationPosition', e.target.value)}
        disabled={!formData.destinationPuck}
      >
        {!formData.destinationPuck && <MenuItem value="">Select a puck first</MenuItem>}
        {formData.destinationPuck && !slotsLoaded && <MenuItem value="">Loading slots...</MenuItem>}
        {formData.destinationPuck && slotsLoaded && availablePositions.length === 0 && (
          <MenuItem value="">No empty slots available</MenuItem>
        )}
        {availablePositions.map((slot) => (
          <MenuItem key={slot.position} value={slot.position.toString()}>
            Slot {slot.position}
          </MenuItem>
        ))}
      </TextField>
    </BaseFormDialog>
  );
};
