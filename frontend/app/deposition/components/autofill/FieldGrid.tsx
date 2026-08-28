'use client';

import { Box, Typography } from '@mui/material';

import { autofilledValue, provenance, type FieldDef } from './fields';
import { MetadataRow, type FieldValue } from './MetadataRow';

export function NothingToFix() {
  return (
    <Typography variant="body2" color="text.secondary" sx={{ py: 3, textAlign: 'center' }}>
      Nothing to fix here - everything’s filled in.
    </Typography>
  );
}

export function FieldGrid({
  fields,
  meta,
  columns,
  readOnly,
  loading,
  onChange,
}: {
  fields: FieldDef[];
  meta: Record<string, FieldValue>;
  columns: 1 | 2;
  readOnly: boolean;
  loading?: boolean;
  onChange: (key: string, value: FieldValue) => void;
}) {
  return (
    <Box
      sx={{
        display: 'grid',
        gridTemplateColumns: columns === 2 ? { xs: '1fr', md: '1fr 1fr' } : '1fr',
        columnGap: { xs: 2, md: 5 },
        rowGap: 1.25,
        alignItems: 'center',
      }}
    >
      {fields.map((field) => (
        <MetadataRow
          key={field.key}
          field={field}
          value={meta[field.key]}
          provenance={provenance(field, meta as never)}
          original={autofilledValue(field, meta as never)}
          readOnly={readOnly}
          loading={loading}
          onChange={(v) => onChange(field.key, v)}
        />
      ))}
    </Box>
  );
}
