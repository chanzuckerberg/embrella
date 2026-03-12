'use client';

import React from 'react';
import { Dialog, DialogContent, DialogTitle } from '@czi-sds/components';
import { SessionForm } from './SessionForm';
import { CreatedSession } from '../types';

interface SessionFormDialogProps {
  open: boolean;
  onClose: () => void;
  onSuccess: (session: CreatedSession) => void;
}

export function SessionFormDialog({ open, onClose, onSuccess }: SessionFormDialogProps) {
  return (
    <Dialog open={open} onClose={onClose} sdsSize="s">
      <DialogTitle title="Create TEM Session" onClose={onClose} />
      <DialogContent>
        <SessionForm
          compact
          onSuccess={(session) => {
            onSuccess(session);
            onClose();
          }}
          onCancel={onClose}
        />
      </DialogContent>
    </Dialog>
  );
}
