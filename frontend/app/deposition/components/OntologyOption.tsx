'use client';

import { Box, Typography } from '@mui/material';

import type { OntologyTerm } from '../services/ols';

export function OntologyOption({ term }: { term: OntologyTerm }) {
  return (
    <Box>
      <Typography variant="body2">
        {term.label}{' '}
        <Typography component="span" variant="caption" color="text.secondary" sx={{ fontFamily: 'monospace' }}>
          {term.id}
        </Typography>
      </Typography>
      {term.synonyms.length > 0 && (
        <Typography variant="caption" color="text.secondary">
          syn: {term.synonyms.slice(0, 3).join(', ')}
        </Typography>
      )}
    </Box>
  );
}
