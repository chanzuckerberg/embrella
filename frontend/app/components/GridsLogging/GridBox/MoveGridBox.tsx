'use client';

import React, { useState, useEffect, useMemo } from 'react';
import { Box, TextField, MenuItem, Tooltip, Typography, Alert } from '@mui/material';
import { Icon } from '@czi-sds/components';
import { PuckList, GridBoxDetailResponse, UserList } from '@app/common/types/gridLogging';
import { useGridLoggingPucksByCane, useGridLoggingPuckSlots , useMoveGridBox, useGridLoggingCaneList} from '@app/common/hooks/useGridLogging';
import { BaseFormDialog } from '@app/common/components/Forms/BaseFormDialog';

interface MoveGridBoxProps {
  open: boolean;
  onClose: () => void;
  currentPuck: PuckList | null;
  currentSlot: number | null;
  gridBoxData: GridBoxDetailResponse | null;
  selectedUser?: UserList | null;
  onSuccess?: (newPuckId: number, newSlotPosition: number) => void;
}

export const MoveGridBox: React.FC<MoveGridBoxProps> = ({
  open,
  onClose,
  currentPuck,
  currentSlot,
  gridBoxData,
  selectedUser,
  onSuccess,
}) => {
  const [formData, setFormData] = useState({
    destinationCane: '',
    destinationPuck: '',
    destinationPosition: '',
  });

  const { moveGridBox, isMoving, error, clearError } = useMoveGridBox();
  const { canes, isSuccess: canesLoaded } = useGridLoggingCaneList();
  const { pucks: pucksInCane, isSuccess: pucksLoaded } = useGridLoggingPucksByCane(
    formData.destinationCane ? Number(formData.destinationCane) : undefined
  );
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
      clearError();
    }
  }, [open, clearError]);

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

  const handleMove = async () => {
    if (!formData.destinationCane || !formData.destinationPuck || !formData.destinationPosition) {
      alert('Please select cane, puck, and position');
      return;
    }

    if (!gridBoxData?.grid_box?.grid_box_id) {
      alert('Grid box ID not found');
      return;
    }

    const destinationPuckId = Number(formData.destinationPuck);
    const destinationPosition = Number(formData.destinationPosition);

    const result = await moveGridBox({
      grid_box_id: gridBoxData.grid_box.grid_box_id,
      destination_puck_id: destinationPuckId,
      destination_position: destinationPosition,
    });

    if (result?.success) {
      onClose();
      if (onSuccess) {
        onSuccess(destinationPuckId, destinationPosition);
      }
    }   
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
      title="Move Grid Box"
      titleExtra={
        <Box sx={{ display: 'flex', justifyContent: 'flex-end', mt: -2 }}>
          <Tooltip title={currentLocationTooltip} arrow placement="right">
            <Box sx={{ display: 'flex', alignItems: 'center', cursor: 'help' }}>
              <Icon sdsIcon="InfoCircle" sdsSize="s" />
            </Box>
          </Tooltip>
        </Box>
      }
      subtitle={selectedUser?.full_name || ''}
      onSave={handleMove}
      isSubmitting={isMoving}
      saveButtonText="Move"
      disabled={!isFormValid || !canesLoaded}
    >
    {Boolean(error) && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={clearError}>
          {error}
        </Alert>
    )}
      <TextField
        select
        required
        fullWidth
        label="Cane"
        value={formData.destinationCane}
        onChange={(e) => handleInputChange('destinationCane', e.target.value)}
      >
        {!canesLoaded && <MenuItem value="">Loading canes...</MenuItem>}
        {canesLoaded && canes.length === 0 && (
          <MenuItem value="">No canes available</MenuItem>
        )}
        {canes.map((cane) => (
          <MenuItem key={cane.id} value={cane.id.toString()}>
            {cane.color_code} Cane (Pos: {cane.position_in_dewar})
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
        {Boolean(formData.destinationCane) && !pucksLoaded && <MenuItem value="">Loading pucks...</MenuItem>}
        {Boolean(formData.destinationCane) &&
          pucksLoaded &&
          (!pucksInCane?.pucks || pucksInCane.pucks.length === 0) && (
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
        {Boolean(formData.destinationPuck) && !slotsLoaded && <MenuItem value="">Loading slots...</MenuItem>}
        {Boolean(formData.destinationPuck) && slotsLoaded && availablePositions.length === 0 && (
          <MenuItem value="">No empty slots available</MenuItem>
        )}
        {slotsData?.slots?.map((slot) => {
          const isFilled = slot.status === 'filled';
          return (
            <MenuItem key={slot.position} value={slot.position.toString()} disabled={isFilled}>
              Slot {slot.position} {isFilled ? '(Filled)' : '(Available)'}
            </MenuItem>
          );
        })}
      </TextField>
    </BaseFormDialog>
  );
};