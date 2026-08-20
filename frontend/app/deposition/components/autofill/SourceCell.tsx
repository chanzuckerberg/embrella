'use client';

import CheckIcon from '@mui/icons-material/Check';
import ErrorOutlineIcon from '@mui/icons-material/ErrorOutline';
import { Box, Tooltip, Typography } from '@mui/material';

import type { Provenance } from './fields';

export function SourceCell({
  provenance,
  original,
  filled,
}: {
  provenance: Provenance;
  original?: unknown;
  filled: boolean;
}) {
  if (provenance === 'required') {
    return (
      <Tooltip title="Required for deposition — auto-fill can’t derive it, so enter it manually.">
        <Box sx={{ display: 'inline-flex', alignItems: 'center', gap: 0.5, color: 'error.main', whiteSpace: 'nowrap' }}>
          <ErrorOutlineIcon sx={{ fontSize: 15 }} />
          <Typography variant="caption" sx={{ fontWeight: 700, letterSpacing: 0.3 }}>
            REQUIRED
          </Typography>
        </Box>
      </Tooltip>
    );
  }

  let note = '';
  let help = '';
  if (provenance === 'mdoc') {
    note = 'mdoc';
    help = 'Auto-filled by cryoetportalprep from the AreTomo3 session.';
  } else if (provenance === 'overridden') {
    note = original != null && original !== '' ? `was ${original}` : 'edited';
    help =
      original != null ? `Auto-fill produced "${original}"; you changed it.` : 'Changed from the auto-filled value.';
  }

  if (!filled && !note) {
    return (
      <Typography variant="caption" sx={{ color: 'text.disabled' }}>
        —
      </Typography>
    );
  }

  return (
    <Tooltip title={help || 'Set.'}>
      <Box sx={{ display: 'inline-flex', alignItems: 'center', gap: 0.5, whiteSpace: 'nowrap' }}>
        <CheckIcon sx={{ fontSize: 15, color: 'success.main' }} />
        {note && (
          <Typography
            variant="caption"
            sx={{ color: provenance === 'overridden' ? 'warning.dark' : 'text.secondary', fontWeight: 500 }}
          >
            {note}
          </Typography>
        )}
      </Box>
    </Tooltip>
  );
}
