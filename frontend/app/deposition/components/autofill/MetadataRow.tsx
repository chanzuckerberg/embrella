'use client';

import { Box, CircularProgress, MenuItem, TextField, Typography } from '@mui/material';

import type { FieldDef, Provenance } from './fields';
import { SourceCell } from './SourceCell';

export type FieldValue = string | number | boolean | null | undefined;

const LABEL_COL = '13rem';
const CAPTION_COL = '5.5rem';

export function MetadataRow({
  field,
  value,
  provenance,
  original,
  readOnly,
  loading,
  placeholder = '-',
  onChange,
}: {
  field: FieldDef;
  value: FieldValue;
  provenance: Provenance;
  original?: unknown;
  readOnly: boolean;
  loading?: boolean;
  /** Placeholder shown when the field is empty (default "-"). */
  placeholder?: string;
  onChange: (value: FieldValue) => void;
}) {
  const label = field.unit ? `${field.label} (${field.unit})` : field.label;
  const shown =
    value ?? (field.default as FieldValue | undefined) ?? (field.readOnly ? (original as FieldValue) : undefined);
  const filled = field.type === 'boolean' ? true : shown != null && shown !== '';
  const showBusy = Boolean(loading) && !filled && Boolean(field.autofillPath);
  const isRequired = !showBusy && provenance === 'required';
  const locked = field.readOnly === true;

  const handleChange = (raw: string) => {
    if (field.type === 'number') onChange(raw === '' ? null : Number(raw));
    else onChange(raw);
  };

  const inputSx = {
    '& .MuiInputBase-root': { minHeight: 34 },
    '& .MuiInputBase-input': { py: 0.75, px: 1.25, fontSize: '0.8125rem' },
  };

  let control;
  if (locked) {
    control = (
      <TextField
        fullWidth
        size="small"
        value={filled ? String(shown) : ''}
        placeholder={placeholder}
        disabled
        sx={inputSx}
      />
    );
  } else if (field.type === 'boolean') {
    control = (
      <TextField
        select
        fullWidth
        size="small"
        value={shown === true ? 'true' : 'false'}
        disabled={readOnly}
        onChange={(e) => onChange(e.target.value === 'true')}
        sx={inputSx}
      >
        <MenuItem value="false">false</MenuItem>
        <MenuItem value="true">true</MenuItem>
      </TextField>
    );
  } else {
    control = (
      <TextField
        fullWidth
        size="small"
        type={field.type === 'number' ? 'number' : 'text'}
        value={shown ?? ''}
        disabled={readOnly}
        error={isRequired}
        placeholder={placeholder}
        onChange={(e) => handleChange(e.target.value)}
        sx={inputSx}
      />
    );
  }

  let captionNode;
  if (showBusy) {
    captionNode = <CircularProgress size={12} thickness={5} sx={{ color: 'text.disabled' }} />;
  } else if (isRequired) {
    captionNode = (
      <Typography variant="caption" noWrap sx={{ color: 'error.main' }}>
        required
      </Typography>
    );
  } else {
    captionNode = <SourceCell provenance={provenance} original={original} />;
  }

  return (
    <Box
      sx={{
        display: 'grid',
        gridTemplateColumns: `${LABEL_COL} minmax(0, 1fr) ${CAPTION_COL}`,
        alignItems: 'center',
        columnGap: 2,
        minWidth: 0,
      }}
    >
      <Typography
        variant="body2"
        noWrap
        title={label}
        sx={{ color: 'text.primary', fontSize: '0.8125rem', minWidth: 0 }}
      >
        {label}
      </Typography>

      {control}

      <Box sx={{ display: 'flex', alignItems: 'center', minWidth: 0 }}>{captionNode}</Box>
    </Box>
  );
}
