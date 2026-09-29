'use client';

import React, { useState } from 'react';
import { PuckList } from '@app/common/types/gridLogging';
import { GridBoxDetailResponse } from '@app/common/types/gridLogging';
import { DJANGO_URL } from '@app/common/constants/api';
import { deleteResource } from '@app/common/queries/fetchResource';
import { ConfirmDialog } from '@app/common/components/Forms/ConfirmDialog';

interface DeleteGridBoxProps {
  open: boolean;
  onClose: () => void;
  selectedPuck: PuckList | null;
  selectedSlot: number | null;
  gridBoxData: GridBoxDetailResponse | null;
  onGridBoxDeleted: () => void;
}

export const DeleteGridBox: React.FC<DeleteGridBoxProps> = ({
  open,
  onClose,
  selectedPuck,
  selectedSlot,
  gridBoxData,
  onGridBoxDeleted,
}) => {
  const [isDeleting, setIsDeleting] = useState(false);
  const gridBoxId = gridBoxData?.grid_box?.grid_box_id;

  if (!selectedPuck || !gridBoxId) return null;

  // Get the grid box name from gridBoxData
  const gridBoxName = gridBoxData?.grid_box?.name || `Grid Box at position ${selectedSlot}`;

  // Check if this grid box has any grids
  const hasGrids = gridBoxData?.grid_box?.positions?.some((position) => position.occupied) || false;

  const handleConfirmDelete = async () => {
    if (!selectedPuck || !gridBoxId) return;
    setIsDeleting(true);

    try {
      const response = await deleteResource(`${DJANGO_URL}/api/list/pucks/grid-box/${gridBoxId}/`);

      const data = await response.json();

      if (response.ok && data.success) {
        if (onGridBoxDeleted) {
          onGridBoxDeleted();
        }
        // Close the dialog
        onClose();
      } else {
        const errorMessage = data.error || data.detail || 'Failed to delete grid box';
        console.error('Failed to delete grid box:', errorMessage);
        setIsDeleting(false);
      }
    } catch (error) {
      console.error('Error deleting grid box:', error);
      setIsDeleting(false);
    }
  };

  return (
    <ConfirmDialog
      open={open}
      onClose={onClose}
      onConfirm={handleConfirmDelete}
      intent={hasGrids ? 'danger' : 'warning'}
      title={`Delete Grid Box ${gridBoxName}?`}
      heading={
        hasGrids ? `Gridbox ${selectedSlot} has filled grids!` : 'This Gridbox is empty and can be safely deleted.'
      }
      body={
        hasGrids
          ? 'if proceeding with deleting, all grids in the gridbox will be trashed'
          : 'Would you like to proceed with deleting this gridbox?'
      }
      submittingText="Deleting..."
      isSubmitting={isDeleting}
    />
  );
};
