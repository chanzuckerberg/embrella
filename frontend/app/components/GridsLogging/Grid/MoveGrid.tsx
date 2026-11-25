'use client';

/**
 * Move a grid: the location picker opens on the grid's box; any free position in any box is a destination.
 */

import React, { useState } from 'react';
import { PuckList, GridDetailsResponse } from '@app/common/types/gridLogging';
import { useMoveGrid } from '@app/common/hooks/useGridLogging/move/useMoveGrid';
import { LocationPickerDialog, PickedLocation, PickTarget } from '../LocationPicker';

const MOVE = 'Move';

interface MoveGridProps {
  open: boolean;
  onClose: () => void;
  currentPuck: PuckList | null;
  currentSlot: number | null;
  gridDetails: GridDetailsResponse | null;
  gridId: number | null;
  onSuccess?: (newPuckId: number, newSlotPosition: number, newGridBoxId: number, newPositionInBox: number) => void;
}

export const MoveGrid: React.FC<MoveGridProps> = ({
  open,
  onClose,
  currentPuck,
  currentSlot,
  gridDetails,
  gridId,
  onSuccess,
}) => {
  const { moveGrid, isMoving, error, clearError } = useMoveGrid();

  // Clear a previous failure when the dialog opens.
  const [wasOpen, setWasOpen] = useState(open);
  if (open !== wasOpen) {
    setWasOpen(open);
    if (open) clearError();
  }

  const handleMove = async ([destination]: PickedLocation[]) => {
    if (!destination?.gridBoxId || destination.position === undefined || !gridId) return;

    const result = await moveGrid({
      grid_id: gridId,
      destination_grid_box_id: destination.gridBoxId,
      destination_position: destination.position,
    });
    if (!result?.success) return;

    onClose();
    onSuccess?.(destination.puckId, destination.slot, destination.gridBoxId, destination.position);
  };

  return (
    <LocationPickerDialog
      open={open}
      onClose={onClose}
      onConfirm={handleMove}
      title={`Move ${gridDetails?.grid_name ?? 'grid'}`}
      target={PickTarget.EmptyPosition}
      start={currentPuck ? { puckId: currentPuck.id, slot: currentSlot ?? undefined } : undefined}
      confirmLabel={() => MOVE}
      error={error}
      onDismissError={clearError}
      busy={isMoving}
    />
  );
};
