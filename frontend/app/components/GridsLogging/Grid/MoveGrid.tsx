'use client';

import React, { useState, useEffect, useMemo } from 'react';
import { Box, TextField, MenuItem, Tooltip, Typography, Alert } from '@mui/material';
import { Icon } from '@czi-sds/components';
import { PuckList } from '@app/common/types/gridLogging/puckList';
import { GridDetailsResponse } from '@app/common/types/gridLogging/gridDetails';
import { UserList } from '@app/common/types/gridLogging/userList';
import { useGridLoggingPucksByCane } from '@app/common/hooks/useGridLogging/useGridLoggingPuckList';
import { useGridLoggingPuckSlots } from '@app/common/hooks/useGridLogging/useGridLoggingPuckSlots';
import { useGridLoggingGridBoxDetail } from '@app/common/hooks/useGridLogging/useGridLoggingGridBoxDetail';
import { useGridLoggingChoices } from '@app/common/hooks/useGridLogging/useGridLoggingChoices';
import { BaseFormDialog } from '@app/common/components/Forms/BaseFormDialog';
import { useMoveGrid } from '@app/common/hooks/useGridLogging/useMoveGrid';
import { useGridLoggingCaneList } from '@app/common/hooks/useGridLogging/useCaneList';

interface MoveGridProps {
  open: boolean;
  onClose: () => void;
  currentPuck: PuckList | null;
  currentSlot: number | null;
  currentPosition: number | null;
  gridDetails: GridDetailsResponse | null;
  gridId: number | null;
  selectedUser?: UserList | null;
  onSuccess?: (newPuckId: number, newSlotPosition: number, newGridBoxId: number, newPositionInBox: number) => void;
}

export const MoveGrid: React.FC<MoveGridProps> = ({
  open,
  onClose,
  currentPuck,
  currentSlot,
  currentPosition,
  gridDetails,
  gridId,
  selectedUser,
  onSuccess,
}) => {
  const [formData, setFormData] = useState({
    destinationCane: '',
    destinationPuck: '',
    destinationSlot: '',
    destinationPosition: '',
  });

  // Use the hook for moving grid
  const { moveGrid, isMoving, error, clearError } = useMoveGrid();

  // Fetch choices (for cane colors)
  const { choices, isSuccess: choicesLoaded } = useGridLoggingChoices();
  const { canes, isSuccess: canesLoaded } = useGridLoggingCaneList();



  // Fetch pucks for selected cane (dynamically)
  const { pucks: pucksInCane, isSuccess: pucksLoaded } = useGridLoggingPucksByCane(
    formData.destinationCane ? Number(formData.destinationCane) : undefined
  );

  // Fetch available slots for selected puck
  const { slotsData, isSuccess: slotsLoaded } = useGridLoggingPuckSlots(
    formData.destinationPuck ? Number(formData.destinationPuck) : undefined
  );

  // Fetch grid box details for selected slot
  const { gridBoxData, isSuccess: gridBoxLoaded } = useGridLoggingGridBoxDetail(
    formData.destinationPuck ? Number(formData.destinationPuck) : undefined,
    formData.destinationSlot ? Number(formData.destinationSlot) : undefined
  );

  // Reset form when dialog opens
  useEffect(() => {
    if (open) {
      setFormData({
        destinationCane: '',
        destinationPuck: '',
        destinationSlot: '',
        destinationPosition: '',
      });
      clearError();
    }
  }, [open, clearError]);

  // Get available slots (filled with grid boxes only) from the puck slots API
  const availableSlots = useMemo(() => {
    if (!slotsData?.slots) return [];
    return slotsData.slots.filter((slot) => slot.status === 'filled');
  }, [slotsData]);

  // Get available positions (empty only) from the grid box
  const availablePositions = useMemo(() => {
    if (!gridBoxData?.grid_box?.positions) return [];
    return gridBoxData.grid_box.positions.filter((pos) => !pos.occupied);
  }, [gridBoxData]);

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
        destinationSlot: '',
        destinationPosition: '',
      }));
    } else if (field === 'destinationPuck') {
      setFormData((prev) => ({
        ...prev,
        destinationSlot: '',
        destinationPosition: '',
      }));
    } else if (field === 'destinationSlot') {
      setFormData((prev) => ({
        ...prev,
        destinationPosition: '',
      }));
    }
  };

  const handleMove = async () => {
    if (
      !formData.destinationCane ||
      !formData.destinationPuck ||
      !formData.destinationSlot ||
      !formData.destinationPosition
    ) {
      return;
    }

    if (!gridId) {
      return;
    }

    // Get the grid box ID from the selected slot
    const selectedSlot = slotsData?.slots?.find(
      (slot) => slot.position === Number(formData.destinationSlot)
    );

    if (!selectedSlot?.grid_box_id) {
      return;
    }

    const destinationPuckId = Number(formData.destinationPuck);
    const destinationSlotPosition = Number(formData.destinationSlot);
    const destinationGridBoxId = selectedSlot.grid_box_id;
    const destinationPosition = Number(formData.destinationPosition);

    const result = await moveGrid({
      grid_id: gridId,
      destination_grid_box_id: destinationGridBoxId,
      destination_position: destinationPosition,
    });

    if (result?.success) {
      onClose();
      if (onSuccess) {
        onSuccess(destinationPuckId, destinationSlotPosition, destinationGridBoxId, destinationPosition);
      }
    }
  };

  const isFormValid =
    formData.destinationCane &&
    formData.destinationPuck &&
    formData.destinationSlot &&
    formData.destinationPosition;

  // Tooltip content showing current location
  const currentLocationTooltip = (
    <Box sx={{ p: 1 }}>
      <Typography variant="body2" sx={{ fontWeight: 'bold', mb: 0.5 }}>
        Current Location:
      </Typography>
      <Typography variant="caption" display="block">
        Grid: {gridDetails?.grid_name || 'N/A'}
      </Typography>
      <Typography variant="caption" display="block">
        Grid Box: {gridDetails?.location?.grid_box_name || 'N/A'}
      </Typography>
      <Typography variant="caption" display="block">
        Puck: {currentPuck?.name || 'N/A'}
      </Typography>
      <Typography variant="caption" display="block">
        Slot: {currentSlot || 'N/A'}
      </Typography>
      <Typography variant="caption" display="block">
        Position: {currentPosition || 'N/A'}
      </Typography>
    </Box>
  );

  return (
    <BaseFormDialog
      open={open}
      onClose={onClose}
      title="Move Grid"
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
        label="Destination Cane"
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
        label="Destination Puck"
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
            CZII-0{puck.name} - Pos {puck.position_in_cane} ({puck.color_display})
          </MenuItem>
        ))}
      </TextField>

      <TextField
        select
        required
        fullWidth
        label="Slot"
        helperText="Select a slot that contains a grid box"
        value={formData.destinationSlot}
        onChange={(e) => handleInputChange('destinationSlot', e.target.value)}
        disabled={!formData.destinationPuck}
      >
        {!formData.destinationPuck && <MenuItem value="">Select a puck first</MenuItem>}
        {Boolean(formData.destinationPuck) && !slotsLoaded && <MenuItem value="">Loading slots...</MenuItem>}
        {Boolean(formData.destinationPuck) && slotsLoaded && availableSlots.length === 0 && (
          <MenuItem value="">No grid boxes available in slots</MenuItem>
        )}
        {slotsData?.slots?.map((slot) => {
            const isFilled = slot.status === 'filled';
            return (
                <MenuItem key={slot.position} value={slot.position.toString()} disabled={!isFilled}>
                Slot {slot.position} {isFilled ? `(GridBox: ${slot.grid_box_name || 'N/A'})` : '(Empty - No Grid Box)'}
                </MenuItem>
            );
        })}
      </TextField>

      <TextField
        select
        required
        fullWidth
        label="Destination Position in Grid Box"
        value={formData.destinationPosition}
        onChange={(e) => handleInputChange('destinationPosition', e.target.value)}
        disabled={!formData.destinationSlot}
      >
        {!formData.destinationSlot && <MenuItem value="">Select a grid box first</MenuItem>}
        {Boolean(formData.destinationSlot) && !gridBoxLoaded && <MenuItem value="">Loading positions...</MenuItem>}
        {Boolean(formData.destinationSlot) && gridBoxLoaded && availablePositions.length === 0 && (
          <MenuItem value="">No empty positions available</MenuItem>
        )}
        {gridBoxData?.grid_box?.positions?.map((position) => {
        const isOccupied = position.occupied;
        const gridName = position.grid_name ? ` (${position.grid_name})` : '';
        return (
            <MenuItem key={position.q} value={position.q.toString()} disabled={isOccupied}>
            {/* Position {position.q} {isOccupied ? `- filled with Grid - ${gridName}` : '- Available'} */}
            Position {position.q} {isOccupied ? `- filled` : '- Available'}
            </MenuItem>
        );
        })}
      </TextField>
    </BaseFormDialog>
  );
};