'use client';

import React, { useState } from 'react';
import { PuckSlotsResponse, PuckList } from '@app/common/types/gridLogging';
import { DJANGO_URL } from '@app/common/constants/api';
import { deleteResource } from '@app/common/queries/fetchResource';
import { ConfirmDialog } from '@app/common/components/Forms/ConfirmDialog';

interface DeletePuckProps {
  open: boolean;
  onClose: () => void;
  selectedPuck: PuckList | null;
  slotsData: PuckSlotsResponse | null;
  onDeleteSuccess?: () => void;
}

export const DeletePuck: React.FC<DeletePuckProps> = ({ open, onClose, selectedPuck, slotsData, onDeleteSuccess }) => {
  const [isDeleting, setIsDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!selectedPuck || !slotsData) return null;

  const hasFilledGridBoxes = slotsData.slot_summary.filled_count > 0;

  const handleConfirmDelete = async () => {
    if (!selectedPuck) return;

    setIsDeleting(true);
    setError(null);

    try {
      const response = await deleteResource(`${DJANGO_URL}/api/list/pucks/${selectedPuck.id}/`);

      const data = await response.json();

      if (response.ok && data.success) {
        if (onDeleteSuccess) {
          onDeleteSuccess();
        }
        // Close the dialog
        onClose();
      } else {
        const errorMessage = data.error || data.detail || 'Failed to delete puck';
        setError(errorMessage);
        setIsDeleting(false);
      }
    } catch {
      setError('An unexpected error occurred while deleting the puck. Please try again.');
      setIsDeleting(false);
    }
  };

  return (
    <ConfirmDialog
      open={open}
      onClose={onClose}
      onConfirm={handleConfirmDelete}
      intent={hasFilledGridBoxes ? 'danger' : 'warning'}
      title={`Delete Puck CZII-0${selectedPuck.name}?`}
      heading={
        hasFilledGridBoxes
          ? `Puck CZII-0${selectedPuck.name} has filled grid boxes!`
          : 'This puck is empty and can be safely deleted.'
      }
      body={
        hasFilledGridBoxes
          ? 'If proceeding with deleting, all grids in the puck will be trashed'
          : 'Would you like to proceed with deleting this puck?'
      }
      submittingText="Deleting..."
      isSubmitting={isDeleting}
      error={error}
    />
  );
};
