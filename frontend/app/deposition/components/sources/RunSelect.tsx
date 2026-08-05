'use client';

import { Box, FormControl, MenuItem, Select, Typography } from '@mui/material';

import { NONE_RUN } from './types';

export function RunSelect({
  label,
  required,
  value,
  options,
  loading,
  disabled,
  placeholder,
  allowNone,
  noneLabel = 'None',
  onChange,
}: {
  label: string;
  required?: boolean;
  value: string;
  options: string[];
  loading: boolean;
  disabled: boolean;
  placeholder: string;
  allowNone?: boolean;
  noneLabel?: string;
  onChange: (value: string) => void;
}) {
  return (
    <Box>
      <Typography variant="body2" sx={{ fontWeight: 600, mb: 0.5 }}>
        {label}
        {required ? ' *' : ''}
      </Typography>
      <FormControl fullWidth size="small" disabled={disabled}>
        <Select
          displayEmpty
          MenuProps={{ PaperProps: { sx: { maxHeight: 180 } } }}
          value={allowNone ? value || NONE_RUN : value}
          onChange={(e) => {
            const v = String(e.target.value);
            onChange(allowNone && v === NONE_RUN ? '' : v);
          }}
          renderValue={(v) => {
            if (v && v !== NONE_RUN) return String(v);
            if (allowNone) return noneLabel;
            return <Typography color="text.disabled">{placeholder}</Typography>;
          }}
        >
          {allowNone && <MenuItem value={NONE_RUN}>{noneLabel}</MenuItem>}
          {loading && <MenuItem disabled>Loading…</MenuItem>}
          {options.map((o) => (
            <MenuItem key={o} value={o}>
              {o}
            </MenuItem>
          ))}
        </Select>
      </FormControl>
    </Box>
  );
}
