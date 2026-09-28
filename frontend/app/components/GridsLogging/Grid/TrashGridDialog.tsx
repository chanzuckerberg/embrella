'use client';

import React from 'react';
import { ConfirmDialog } from '@app/common/components/Forms/ConfirmDialog';

interface TrashGridDialogProps {
  open: boolean;
  onClose: () => void;
  onConfirm: () => void;
  isProcessing: boolean;
}

export const TrashGridDialog: React.FC<TrashGridDialogProps> = ({ open, onClose, onConfirm, isProcessing }) => (
  <ConfirmDialog
    open={open}
    onClose={onClose}
    onConfirm={onConfirm}
    intent="warning"
    title="Trash this grid?"
    heading="This action will remove the grid from its current box and puck location."
    body="This cannot be automatically undone."
    submittingText="Trashing..."
    isSubmitting={isProcessing}
  />
);
