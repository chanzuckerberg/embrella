'use client';

import type { ReactNode } from 'react';
import { Button } from '@czi-sds/components';
import CheckCircleOutlineIcon from '@mui/icons-material/CheckCircleOutline';
import ErrorOutlineIcon from '@mui/icons-material/ErrorOutline';
import { Box, CircularProgress, Typography } from '@mui/material';

import type { SaveStatus } from '../hooks/useDraftAutoSave';

const TIME = { hour: '2-digit', minute: '2-digit', second: '2-digit' } as const;
const ICON_SX = { fontSize: 16 } as const;

export function SaveIndicator({
  status,
  lastSavedAt,
  onSaveNow,
}: {
  status: SaveStatus;
  lastSavedAt: Date | null;
  onSaveNow: () => void;
}) {
  // Nothing to show until there's an actual save state — no default "autosave" label.
  let icon: ReactNode = null;
  let label = '';
  let color: 'text.secondary' | 'error.main' = 'text.secondary';

  if (status === 'saving') {
    icon = <CircularProgress size={14} />;
    label = 'Saving…';
  } else if (status === 'error') {
    icon = <ErrorOutlineIcon sx={{ ...ICON_SX, color: 'error.main' }} />;
    label = 'Save failed — retry';
    color = 'error.main';
  } else if (status === 'saved' || lastSavedAt) {
    icon = <CheckCircleOutlineIcon sx={{ ...ICON_SX, color: 'success.main' }} />;
    const at = lastSavedAt ? ` · ${lastSavedAt.toLocaleTimeString([], TIME)}` : '';
    label = `Saved${at}`;
  }

  return (
    <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.75 }}>
      {label && icon}
      {label && (
        <Typography variant="caption" sx={{ color }}>
          {label}
        </Typography>
      )}
      <Button sdsType="secondary" sdsStyle="minimal" size="small" onClick={onSaveNow} disabled={status === 'saving'}>
        Save now
      </Button>
    </Box>
  );
}
