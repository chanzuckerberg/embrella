'use client';

import { Box, Checkbox, TextField, Typography } from '@mui/material';

import type { FieldDef, Provenance } from './fields';
import { SourceCell } from './SourceCell';

export type FieldValue = string | number | boolean | null | undefined;

export function MetadataRow({
  field,
  value,
  provenance,
  original,
  readOnly,
  onChange,
}: {
  field: FieldDef;
  value: FieldValue;
  provenance: Provenance;
  original?: unknown;
  readOnly: boolean;
  onChange: (value: FieldValue) => void;
}) {
  const label = field.unit ? `${field.label} (${field.unit})` : field.label;
  const filled = field.type === 'boolean' ? true : value != null && value !== '';

  const handleChange = (raw: string) => {
    if (field.type === 'number') onChange(raw === '' ? null : Number(raw));
    else onChange(raw);
  };

  return (
    <>
      <Typography variant="body2" sx={{ color: 'text.primary', whiteSpace: 'nowrap' }}>
        {label}
      </Typography>

      {field.type === 'boolean' ? (
        <Checkbox
          checked={value === true}
          disabled={readOnly}
          size="small"
          sx={{ justifySelf: 'start', p: 0.5 }}
          onChange={(e) => onChange(e.target.checked)}
        />
      ) : (
        <TextField
          fullWidth
          size="small"
          type={field.type === 'number' ? 'number' : 'text'}
          value={value ?? ''}
          disabled={readOnly}
          error={provenance === 'required'}
          placeholder={provenance === 'required' ? 'Set value' : undefined}
          onChange={(e) => handleChange(e.target.value)}
        />
      )}

      <Box sx={{ justifySelf: 'end' }}>
        <SourceCell provenance={provenance} original={original} filled={filled} />
      </Box>
    </>
  );
}
