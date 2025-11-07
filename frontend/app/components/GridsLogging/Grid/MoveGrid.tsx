'use client';

import React, { useState, useEffect, useMemo } from 'react';
import { Box, TextField, MenuItem, Tooltip, Typography } from '@mui/material';
import { Icon } from '@czi-sds/components';
import { PucksList } from '@app/common/types/gridLogging/puckList';
import { GridDetailsResponse } from '@app/common/types/gridLogging/gridDetails';
import { UsersList } from '@app/common/types/gridLogging/userList';
import { useGridLoggingPucksByCane } from '@app/common/hooks/useGridLogging/useGridLoggingPuckList';
import { useGridLoggingPuckSlots } from '@app/common/hooks/useGridLogging/useGridLoggingPuckSlots';
import { useGridLoggingGridBoxDetail } from '@app/common/hooks/useGridLogging/useGridLoggingGridBoxDetail';
import { useGridLoggingChoices } from '@app/common/hooks/useGridLogging/useGridLoggingChoices';
import { BaseFormDialog } from '@app/common/components/Forms/BaseFormDialog';

interface MoveGridProps {
  open: boolean;
  onClose: () => void;
  currentPuck: PucksList | null;
  currentSlot: number | null;
  currentPosition: number | null;
  gridDetails: GridDetailsResponse | null;
  selectedUser?: UsersList | null;
}

export const MoveGrid: React.FC<MoveGridProps> = ({
  open,
  onClose,
  currentPuck,
  currentSlot,
  currentPosition,
  gridDetails,
  selectedUser,
}) => {
  const [formData, setFormData] = useState({
    destinationCane: '',
    destinationPuck: '',
    destinationSlot: '',
    destinationPosition: '',
  });
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Fetch choices (for cane colors)
  const { choices, isSuccess: choicesLoaded } = useGridLoggingChoices();

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
    }
  }, [open]);

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

  const handleMove = () => {
    if (
      !formData.destinationCane ||
      !formData.destinationPuck ||
      !formData.destinationSlot ||
      !formData.destinationPosition
    ) {
      alert('Please select cane, puck, slot, and position');
      return;
    }

    setIsSubmitting(true);

    const selectedPuck = pucksInCane?.pucks?.find((p) => p.id.toString() === formData.destinationPuck);

    console.log('Moving grid:', {
      from: {
        puck: currentPuck?.name,
        puck_id: currentPuck?.id,
        slot: currentSlot,
        position: currentPosition,
        grid_box: gridDetails?.location?.grid_box_name,
      },
      to: {
        cane_id: formData.destinationCane,
        puck: selectedPuck?.name,
        puck_id: formData.destinationPuck,
        slot: formData.destinationSlot,
        grid_box: gridBoxData?.grid_box?.name,
        position: formData.destinationPosition,
      },
      grid: {
        name: gridDetails?.grid_name,
      },
    });
    setTimeout(() => {
      setIsSubmitting(false);
      onClose();
    }, 1000);
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
        <Tooltip title={currentLocationTooltip} arrow placement="right">
          <Box sx={{ display: 'flex', alignItems: 'center', cursor: 'help' }}>
            <Icon sdsIcon="InfoCircle" sdsSize="s" />
          </Box>
        </Tooltip>
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
        label="Destination Cane"
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
            const gridBoxName = gridBoxData?.grid_box?.name;
            console.log('gridBoxName', gridBoxName, slot);
          const isFilled = slot.status === 'filled';
          return (
            <MenuItem key={slot.position} value={slot.position.toString()} disabled={!isFilled}>
              Slot {slot.position} {isFilled ? `(GridBox name: ${gridBoxName || 'N/A'})` : '(Empty)'}
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
          return (
            <MenuItem key={position.q} value={position.q.toString()} disabled={isOccupied}>
              Position {position.q} {isOccupied ? '(Occupied)' : '(Available)'}
            </MenuItem>
          );
        })}
      </TextField>
    </BaseFormDialog>
  );
};