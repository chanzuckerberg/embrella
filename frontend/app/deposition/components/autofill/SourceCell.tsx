'use client';

import { Icon } from '@czi-sds/components';
import { Box, Typography } from '@mui/material';

import type { Provenance } from './fields';

export function SourceCell({ provenance, original }: { provenance: Provenance; original?: unknown }) {
  // Required is shown as a red * on the field label (see MetadataRow); the Source column only marks provenance.
  let note = '';
  if (provenance === 'init') {
    note = 'init';
  } else if (provenance === 'overridden') {
    note = original != null && original !== '' ? `was ${original}` : 'edited';
  }

  if (!note) return null;

  return (
    <Box sx={{ display: 'inline-flex', alignItems: 'center', gap: 0.5, whiteSpace: 'nowrap' }}>
      <Icon sdsIcon="CheckCircle" sdsSize="xxs" color="green" />
      <Typography
        variant="caption"
        sx={{ color: provenance === 'overridden' ? 'warning.dark' : 'text.disabled', fontWeight: 500 }}
      >
        {note}
      </Typography>
    </Box>
  );
}
