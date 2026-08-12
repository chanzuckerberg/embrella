'use client';

import type { ReactNode } from 'react';
import { Box, Paper, Typography } from '@mui/material';

import type { TomogramSubsetMode } from '../../types';
import { rollup } from './counts';
import type { SourceRow } from './types';

function SummaryLine({ label, value }: { label: string; value: ReactNode }) {
  return (
    <Box sx={{ display: 'flex', justifyContent: 'space-between', py: 0.75 }}>
      <Typography variant="body2" color="text.secondary">
        {label}
      </Typography>
      <Typography variant="body2" sx={{ fontWeight: 700 }}>
        {value}
      </Typography>
    </Box>
  );
}

export function DepositionSummary({ rows, subsetMode }: { rows: SourceRow[]; subsetMode: TomogramSubsetMode }) {
  const s = rollup(rows, subsetMode);
  const tomograms = s.totalTomograms > 0 ? `${s.selectedTomograms} of ${s.totalTomograms}` : '—';

  return (
    <Paper variant="outlined" sx={{ p: 2.5, borderRadius: 2, minWidth: 240, position: 'sticky', top: 24 }}>
      <Typography variant="overline" sx={{ color: 'text.secondary', fontWeight: 700, letterSpacing: 1 }}>
        This deposition
      </Typography>
      <Box sx={{ mt: 1 }}>
        <SummaryLine label="Sessions" value={s.sessions} />
        <SummaryLine label="Tomograms" value={tomograms} />
        {subsetMode !== 'all' && s.totalTomograms > 0 && <SummaryLine label="Excluded" value={s.droppedTomograms} />}
        <SummaryLine label="Copick configs" value={s.copickConfigs} />
        <SummaryLine label="Denoised sessions" value={`${s.denoisedSessions} of ${s.sessions}`} />
      </Box>
    </Paper>
  );
}
