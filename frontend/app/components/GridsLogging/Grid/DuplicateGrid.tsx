'use client';

import React, { useState, useEffect, useMemo } from 'react';
import { Box, TextField, MenuItem, Alert, Typography, Tooltip } from '@mui/material';
import { Icon } from '@czi-sds/components';
import { GridDetailsResponse } from '@app/common/types/gridLogging';
import { useGridLoggingPucksByCane } from '@app/common/hooks/useGridLogging/other/useGridLoggingPuckList';
import { useGridLoggingPuckSlots } from '@app/common/hooks/useGridLogging/details/useGridLoggingPuckSlots';
import { useGridLoggingCaneList } from '@app/common/hooks/useGridLogging/list/useCaneList';
import { useDuplicateGrid } from '@app/common/hooks/useGridLogging/duplicate/useDuplicateGrid';
import { useAvailablePositions } from '@app/common/hooks/useGridLogging/duplicate/useAvailablePositions';
import { BaseFormDialog } from '@app/common/components/Forms/BaseFormDialog';

interface DuplicateGridProps {
  open: boolean;
  onClose: () => void;
  gridDetails: GridDetailsResponse | null;
  gridId: number | null;
  initialLocation?: {
    caneId: number | null;
    puckId: number | null;
    slotPosition: number | null;
  } | null;
  onSuccess?: (newGridIds: number[]) => void;
}

export const DuplicateGrid: React.FC<DuplicateGridProps> = ({
  open,
  onClose,
  gridDetails,
  gridId,
  initialLocation,
  onSuccess,
}) => {
  const [formData, setFormData] = useState({
    destinationCane: '',
    destinationPuck: '',
    destinationSlot: '',
    numberToCopy: '1',
  });

  const { duplicateGrid, isDuplicating, error, clearError } = useDuplicateGrid();
  const { canes, isSuccess: canesLoaded } = useGridLoggingCaneList();

  const { pucks: pucksInCane, isSuccess: pucksLoaded } = useGridLoggingPucksByCane(
    formData.destinationCane ? Number(formData.destinationCane) : undefined
  );

  const { slotsData, isSuccess: slotsLoaded } = useGridLoggingPuckSlots(
    formData.destinationPuck ? Number(formData.destinationPuck) : undefined
  );

  const selectedSlot = useMemo(
    () => slotsData?.slots?.find((slot) => slot.position === Number(formData.destinationSlot)),
    [slotsData, formData.destinationSlot]
  );

  const destinationBoxId = selectedSlot?.grid_box_id ?? null;
  const { availablePositions } = useAvailablePositions(destinationBoxId);
  const availableCount = availablePositions?.available_count ?? 0;

  // Reset form when the dialog opens.
  const [wasOpen, setWasOpen] = useState(open);
  if (open !== wasOpen) {
    setWasOpen(open);
    if (open) {
      setFormData({
        destinationCane: '',
        destinationPuck: '',
        destinationSlot: '',
        numberToCopy: '1',
      });
      clearError();
    }
  }

  const prefillCaneId = initialLocation?.caneId ?? null;
  const prefillPuckId = initialLocation?.puckId ?? null;
  const prefillSlotPosition = initialLocation?.slotPosition ?? null;

  // Seed each destination field once its options finish loading async, if not already set.
  /* eslint-disable react-hooks/set-state-in-effect -- reacting to async data arrival; guarded to run once per field */
  useEffect(() => {
    if (!open || !prefillCaneId || !canesLoaded) return;
    if (!canes.some((c) => c.id === prefillCaneId)) return;
    setFormData((prev) => (prev.destinationCane ? prev : { ...prev, destinationCane: prefillCaneId.toString() }));
  }, [open, prefillCaneId, canesLoaded, canes]);

  useEffect(() => {
    if (!open || !prefillPuckId || !pucksLoaded) return;
    if (!pucksInCane?.pucks?.some((p) => p.id === prefillPuckId)) return;
    setFormData((prev) => (prev.destinationPuck ? prev : { ...prev, destinationPuck: prefillPuckId.toString() }));
  }, [open, prefillPuckId, pucksLoaded, pucksInCane]);

  useEffect(() => {
    if (!open || !prefillSlotPosition || !slotsLoaded) return;
    if (!slotsData?.slots?.some((s) => s.position === prefillSlotPosition && s.status === 'filled')) return;
    setFormData((prev) => (prev.destinationSlot ? prev : { ...prev, destinationSlot: prefillSlotPosition.toString() }));
  }, [open, prefillSlotPosition, slotsLoaded, slotsData]);
  /* eslint-enable react-hooks/set-state-in-effect */

  const handleInputChange = (field: string, value: string) => {
    setFormData((prev) => {
      const next = { ...prev, [field]: value };
      if (field === 'destinationCane') {
        next.destinationPuck = '';
        next.destinationSlot = '';
      } else if (field === 'destinationPuck') {
        next.destinationSlot = '';
      }
      return next;
    });
  };

  const numberToCopy = Number(formData.numberToCopy) || 0;
  const numberIsValid = numberToCopy >= 1 && numberToCopy <= availableCount;
  const isFormValid = Boolean(destinationBoxId) && numberIsValid;

  const handleDuplicate = async () => {
    if (!gridId || !destinationBoxId || !numberIsValid) return;

    const result = await duplicateGrid({
      grid_id: gridId,
      destination_grid_box_id: destinationBoxId,
      number_to_copy: numberToCopy,
    });

    if (result?.success) {
      onClose();
      onSuccess?.(result.new_grid_ids);
    }
  };

  const sourceLocation = gridDetails?.location;
  const sourceLocationLabel = sourceLocation
    ? `Puck-CZII-0${sourceLocation.puck_name ?? '?'}/Slot-${sourceLocation.position_in_puck ?? '?'}/Position-${sourceLocation.position_in_box ?? '?'}`
    : '';
  const subtitleNode = (
    <>
      {gridDetails?.grid_name}
      {Boolean(sourceLocationLabel) && (
        <>
          <br />
          {sourceLocationLabel}
        </>
      )}
    </>
  );

  const infoTooltip = (
    <Box sx={{ p: 1, maxWidth: 280 }}>
      <Typography variant="body2" component="div" sx={{ mb: 0.5 }}>
        Creates grid copies, filling the next available positions in the destination grid box.
      </Typography>
      <Typography variant="body2" component="div" sx={{ mb: 0.5 }}>
        Copies inherit the source grid&apos;s metadata (specimen, freezing session, labels, parameters), and are labeled
        by copy number.
      </Typography>
    </Box>
  );

  const availabilityHelperText = (() => {
    if (!destinationBoxId) return 'Pick a destination grid box to see availability.';
    if (availableCount === 0) return 'No empty positions in the selected grid box.';
    return `${availableCount} position${availableCount === 1 ? '' : 's'} available in the selected grid box.`;
  })();

  const positionsAvailableLabel = `${availableCount} ${availableCount === 1 ? 'position' : 'positions'}`;

  return (
    <BaseFormDialog
      open={open}
      onClose={onClose}
      title="Duplicate Grid"
      titleExtra={
        <Tooltip title={infoTooltip} arrow placement="right">
          <Box sx={{ display: 'flex', alignItems: 'center', cursor: 'help' }}>
            <Icon sdsIcon="InfoCircle" sdsSize="s" />
          </Box>
        </Tooltip>
      }
      subtitle={subtitleNode}
      onSave={handleDuplicate}
      isSubmitting={isDuplicating}
      saveButtonText="Duplicate"
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
        {canesLoaded && canes.length === 0 && <MenuItem value="">No canes available</MenuItem>}
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
        label="Destination Grid Box"
        value={formData.destinationSlot}
        onChange={(e) => handleInputChange('destinationSlot', e.target.value)}
        disabled={!formData.destinationPuck}
      >
        {!formData.destinationPuck && <MenuItem value="">Select a puck first</MenuItem>}
        {Boolean(formData.destinationPuck) && !slotsLoaded && <MenuItem value="">Loading slots...</MenuItem>}
        {slotsData?.slots?.map((slot) => {
          const isFilled = slot.status === 'filled';
          return (
            <MenuItem key={slot.position} value={slot.position.toString()} disabled={!isFilled}>
              Slot {slot.position} {isFilled ? `(GridBox: ${slot.grid_box_name || 'N/A'})` : '(Empty - No Grid Box)'}
            </MenuItem>
          );
        })}
      </TextField>

      <Typography
        variant="caption"
        color={availableCount > 0 || !destinationBoxId ? 'text.secondary' : 'error'}
        sx={{ display: 'block', mt: 2, mb: 2, ml: 2 }}
      >
        {availabilityHelperText}
      </Typography>

      <Box>
        <TextField
          type="number"
          required
          fullWidth
          label="Number of copies"
          value={formData.numberToCopy}
          onChange={(e) => handleInputChange('numberToCopy', e.target.value)}
          inputProps={{ min: 1, max: Math.max(availableCount, 1) }}
          error={Boolean(destinationBoxId) && !numberIsValid}
          sx={{ mt: 5 }}
          helperText={
            Boolean(destinationBoxId) && !numberIsValid && numberToCopy > availableCount
              ? `Only ${positionsAvailableLabel} available.`
              : ' '
          }
        />
      </Box>
    </BaseFormDialog>
  );
};
