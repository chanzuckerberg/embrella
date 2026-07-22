'use client';

import CloseIcon from '@mui/icons-material/Close';
import { FormControl, IconButton, MenuItem, Select, Stack, TextField, Typography } from '@mui/material';

import type { CrossRef, CrossRefType } from '../types';

const TYPE_LABEL: Record<CrossRefType, string> = {
  publication: 'Publication DOI',
  related_db: 'Related DB entry',
};

const PLACEHOLDER: Record<CrossRefType, string> = {
  publication: '10.1021/…',
  related_db: 'EMD-…, PDB-…',
};

export function CrossReferencesEditor({
  entries,
  onChange,
  disabled = false,
}: {
  entries: CrossRef[];
  onChange: (entries: CrossRef[]) => void;
  disabled?: boolean;
}) {
  const patch = (i: number, next: Partial<CrossRef>) =>
    onChange(entries.map((e, idx) => (idx === i ? { ...e, ...next } : e)));
  const remove = (i: number) => onChange(entries.filter((_, idx) => idx !== i));

  if (entries.length === 0) {
    return (
      <Typography variant="body2" color="text.secondary">
        No cross references yet.
      </Typography>
    );
  }

  return (
    <Stack spacing={1.5}>
      {entries.map((entry, i) => (
        <Stack key={i} direction="row" spacing={1} alignItems="center">
          <FormControl size="small" sx={{ minWidth: 170 }}>
            <Select
              value={entry.type}
              disabled={disabled}
              onChange={(e) => patch(i, { type: e.target.value as CrossRefType })}
            >
              <MenuItem value="publication">{TYPE_LABEL.publication}</MenuItem>
              <MenuItem value="related_db">{TYPE_LABEL.related_db}</MenuItem>
            </Select>
          </FormControl>
          <TextField
            size="small"
            fullWidth
            placeholder={PLACEHOLDER[entry.type]}
            value={entry.value}
            disabled={disabled}
            onChange={(e) => patch(i, { value: e.target.value })}
          />
          <IconButton aria-label="Remove entry" size="small" disabled={disabled} onClick={() => remove(i)}>
            <CloseIcon fontSize="small" sx={{ color: 'error.main' }} />
          </IconButton>
        </Stack>
      ))}
    </Stack>
  );
}
