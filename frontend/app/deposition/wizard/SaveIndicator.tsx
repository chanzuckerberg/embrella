'use client';

import { Button } from '@czi-sds/components';
import { Box, CircularProgress, Typography } from '@mui/material';

import type { SaveStatus } from '../hooks/useDraftAutoSave';

const TIME = { hour: '2-digit', minute: '2-digit' } as const;

export function SaveIndicator({
  status,
  lastSavedAt,
  onSaveNow,
}: {
  status: SaveStatus;
  lastSavedAt: Date | null;
  onSaveNow: () => void;
}) {
  let label: React.ReactNode = 'Changes save automatically';
  let color: 'text.secondary' | 'error.main' = 'text.secondary';

  if (status === 'saving') label = 'Saving…';
  else if (status === 'error') {
    label = 'Save failed — retry';
    color = 'error.main';
  } else if (status === 'saved' || lastSavedAt) {
    const at = lastSavedAt ? ` · ${lastSavedAt.toLocaleTimeString([], TIME)}` : '';
    label = `Saved${at}`;
  }

  return (
    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
      {status === 'saving' && <CircularProgress size={14} />}
      <Typography variant="caption" sx={{ color }}>
        {label}
      </Typography>
      <Button sdsType="secondary" sdsStyle="minimal" size="small" onClick={onSaveNow} disabled={status === 'saving'}>
        Save now
      </Button>
    </Box>
  );
}
