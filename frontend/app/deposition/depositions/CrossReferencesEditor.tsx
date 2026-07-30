'use client';

import { Icon } from '@czi-sds/components';
import { Box, FormControl, IconButton, MenuItem, Select, Stack, Typography } from '@mui/material';

import { IdentifierField } from '../components/IdentifierField';
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
        <Stack key={i} direction="row" spacing={1} alignItems="flex-start">
          <FormControl size="small" sx={{ minWidth: 170, height: 40 }}>
            <Select
              value={entry.type}
              disabled={disabled}
              onChange={(e) => patch(i, { type: e.target.value as CrossRefType })}
            >
              <MenuItem value="publication">{TYPE_LABEL.publication}</MenuItem>
              <MenuItem value="related_db">{TYPE_LABEL.related_db}</MenuItem>
            </Select>
          </FormControl>
          <IdentifierField
            kind={entry.type === 'publication' ? 'doi' : 'related_db'}
            size="small"
            fullWidth
            placeholder={PLACEHOLDER[entry.type]}
            value={entry.value}
            disabled={disabled}
            onChange={(v) => patch(i, { value: v })}
          />
          <Box sx={{ display: 'flex', alignItems: 'center', height: 40 }}>
            <IconButton aria-label="Remove entry" size="small" disabled={disabled} onClick={() => remove(i)}>
              <Icon sdsIcon="TrashCan" sdsSize="s" color="gray" />
            </IconButton>
          </Box>
        </Stack>
      ))}
    </Stack>
  );
}
