'use client';

import type { ReactNode } from 'react';
import { Button, Icon } from '@czi-sds/components';
import { Box, CircularProgress, Typography } from '@mui/material';

import type { SaveStatus } from '../hooks/useDraftAutoSave';

const TIME = { hour: '2-digit', minute: '2-digit', second: '2-digit' } as const;

export function SaveIndicator({
  status,
  lastSavedAt,
  onRetry,
}: {
  status: SaveStatus;
  lastSavedAt: Date | null;
  onRetry: () => void;
}) {
  let icon: ReactNode = null;
  let label = '';
  let color: 'text.secondary' | 'error.main' = 'text.secondary';

  if (status === 'saving') {
    icon = <CircularProgress size={14} />;
    label = 'Saving…';
  } else if (status === 'error') {
    icon = <Icon sdsIcon="ExclamationMarkCircle" sdsSize="s" color="red" />;
    label = 'Save failed — retry';
    color = 'error.main';
  } else if (status === 'saved' || lastSavedAt) {
    icon = <Icon sdsIcon="CheckCircle" sdsSize="s" color="green" />;
    const at = lastSavedAt ? ` · ${lastSavedAt.toLocaleTimeString([], TIME)}` : '';
    label = `Saved${at}`;
  }

  if (!label) return null;

  return (
    <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.75 }}>
      {icon}
      <Typography variant="caption" sx={{ color }}>
        {label}
      </Typography>
      {status === 'error' && (
        <Button sdsType="secondary" sdsStyle="minimal" size="small" onClick={onRetry}>
          Retry
        </Button>
      )}
    </Box>
  );
}
