'use client';

import { Box, MenuItem, TextField, Typography } from '@mui/material';

import type { FieldDef, Provenance } from './fields';
import { SourceCell } from './SourceCell';

export type FieldValue = string | number | boolean | null | undefined;

const LABEL_COL = '13.5rem';
const PATH_LABEL_COL = '5.5rem';
const SOURCE_COL = '6.5rem';

export function MetadataRow({
  field,
  value,
  provenance,
  original,
  readOnly,
  wide,
  onChange,
}: {
  field: FieldDef;
  value: FieldValue;
  provenance: Provenance;
  original?: unknown;
  readOnly: boolean;
  wide?: boolean;
  onChange: (value: FieldValue) => void;
}) {
  const label = field.unit ? `${field.label} (${field.unit})` : field.label;
  const shown =
    value ?? (field.default as FieldValue | undefined) ?? (field.readOnly ? (original as FieldValue) : undefined);
  const disabled = readOnly || field.readOnly === true;
  const filled = field.type === 'boolean' ? true : shown != null && shown !== '';
  const isRequired = provenance === 'required';

  const handleChange = (raw: string) => {
    if (field.type === 'number') onChange(raw === '' ? null : Number(raw));
    else onChange(raw);
  };

  return (
    <Box
      sx={{
        display: 'grid',
        gridTemplateColumns: wide
          ? `${PATH_LABEL_COL} minmax(0, 1fr) ${SOURCE_COL}`
          : `${LABEL_COL} minmax(0, 1fr) ${SOURCE_COL}`,
        alignItems: 'center',
        columnGap: 1.5,
        minWidth: 0,
      }}
    >
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.25, minWidth: 0 }}>
        <Typography
          variant="body2"
          noWrap
          sx={{ color: 'text.secondary', fontSize: '0.8125rem', lineHeight: 1.3, minWidth: 0 }}
          title={label}
        >
          {label}
        </Typography>
        {isRequired && (
          <Box component="span" sx={{ color: 'error.main', fontWeight: 700, flexShrink: 0 }}>
            *
          </Box>
        )}
      </Box>

      {field.type === 'boolean' ? (
        <TextField
          select
          fullWidth
          size="small"
          value={shown === true ? 'true' : 'false'}
          disabled={disabled}
          onChange={(e) => onChange(e.target.value === 'true')}
          sx={{
            minWidth: 0,
            '& .MuiInputBase-root': { minHeight: 32 },
            '& .MuiInputBase-input': {
              py: 0.625,
              px: 1,
              fontSize: '0.8125rem',
              textAlign: 'center',
              color: disabled ? 'text.secondary' : undefined,
            },
          }}
        >
          <MenuItem value="false">false</MenuItem>
          <MenuItem value="true">true</MenuItem>
        </TextField>
      ) : (
        <TextField
          fullWidth
          size="small"
          type={field.type === 'number' ? 'number' : 'text'}
          value={shown ?? ''}
          disabled={disabled}
          placeholder={isRequired ? 'Set value' : '-'}
          onChange={(e) => handleChange(e.target.value)}
          sx={{
            minWidth: 0,
            '& .MuiInputBase-root': { minHeight: 32 },
            '& .MuiInputBase-input': {
              py: 0.625,
              px: 1,
              fontSize: '0.8125rem',
              textAlign: wide ? 'left' : 'center',
              color: disabled && filled ? 'text.secondary' : undefined,
              overflow: 'hidden',
              textOverflow: 'ellipsis',
            },
            '& .MuiOutlinedInput-root': {
              ...(isRequired && {
                '& fieldset': { borderColor: 'error.main' },
                '&:hover fieldset': { borderColor: 'error.dark' },
                '&.Mui-focused fieldset': { borderColor: 'error.main' },
              }),
            },
          }}
        />
      )}

      <Box sx={{ pl: 0.5, minWidth: '3.25rem' }}>
        <SourceCell provenance={provenance} original={original} />
      </Box>
    </Box>
  );
}
