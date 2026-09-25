'use client';

import React from 'react';
import { Alert } from '@mui/material';
import { Button, Dialog, DialogActions, DialogContent, DialogTitle } from '@czi-sds/components';
import { CreatedSession } from '../types';
import { SessionSummary } from './SessionSummary';

interface SessionCreatedDialogProps {
  open: boolean;
  session: CreatedSession | null;
  onCreateAnother: () => void;
  onDone: () => void;
}

export function SessionCreatedDialog({ open, session, onCreateAnother, onDone }: SessionCreatedDialogProps) {
  if (!session) return null;

  return (
    <Dialog open={open} onClose={onDone} sdsSize="s">
      <DialogTitle title="Session Created" onClose={onDone} />
      <DialogContent>
        <SessionSummary
          session={session}
          notice={
            <Alert severity="info" sx={{ mt: 1 }}>
              Please review the file directories below and ensure data is stored correctly.
            </Alert>
          }
        />
      </DialogContent>
      <DialogActions>
        <Button sdsType="secondary" sdsStyle="outline" onClick={onCreateAnother}>
          Create Another
        </Button>
        <Button sdsType="primary" sdsStyle="solid" onClick={onDone}>
          Done
        </Button>
      </DialogActions>
    </Dialog>
  );
}
