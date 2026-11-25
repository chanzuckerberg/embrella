'use client';

/**
 * Move a grid box: the location picker opens on the box's puck; any free slot in any puck is a destination.
 */

import React, { useState } from 'react';
import { PuckList, GridBoxDetailResponse } from '@app/common/types/gridLogging';
import { useMoveGridBox } from '@app/common/hooks/useGridLogging';
import { LocationPickerDialog, PickedLocation, PickTarget } from '../LocationPicker';

const MOVE = 'Move';

interface MoveGridBoxProps {
  open: boolean;
  onClose: () => void;
  currentPuck: PuckList | null;
  gridBoxData: GridBoxDetailResponse | null;
  onSuccess?: (newPuckId: number, newSlotPosition: number) => void;
}

export const MoveGridBox: React.FC<MoveGridBoxProps> = ({ open, onClose, currentPuck, gridBoxData, onSuccess }) => {
  const { moveGridBox, isMoving, error, clearError } = useMoveGridBox();

  // Clear a previous failure when the dialog opens.
  const [wasOpen, setWasOpen] = useState(open);
  if (open !== wasOpen) {
    setWasOpen(open);
    if (open) clearError();
  }

  const handleMove = async ([destination]: PickedLocation[]) => {
    const gridBoxId = gridBoxData?.grid_box?.grid_box_id;
    if (!destination || !gridBoxId) return;

    const result = await moveGridBox({
      grid_box_id: gridBoxId,
      destination_puck_id: destination.puckId,
      destination_position: destination.slot,
    });
    if (!result?.success) return;

    onClose();
    onSuccess?.(destination.puckId, destination.slot);
  };

  return (
    <LocationPickerDialog
      open={open}
      onClose={onClose}
      onConfirm={handleMove}
      title={`Move ${gridBoxData?.grid_box?.name ?? 'grid box'}`}
      target={PickTarget.EmptySlot}
      start={currentPuck ? { puckId: currentPuck.id } : undefined}
      confirmLabel={() => MOVE}
      error={error}
      onDismissError={clearError}
      busy={isMoving}
    />
  );
};
