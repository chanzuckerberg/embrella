'use client';

import { type ReactNode } from 'react';
import { Icon } from '@czi-sds/components';
import { Box, TextField, type TextFieldProps } from '@mui/material';

import { useDebounced } from '../hooks/useDebounced';
import { useIdentifierLookup } from '../hooks/useIdentifier';
import {
  DOI_RE,
  normalizeDoi,
  ORCID_RE,
  orcidChecksumOk,
  RELATED_DB_RE,
  type IdentifierKind,
} from '../services/identifiers';

const LABELS: Record<IdentifierKind, { name: string; invalid: string }> = {
  orcid: { name: 'ORCID', invalid: 'Invalid ORCID format' },
  doi: { name: 'DOI', invalid: 'Invalid DOI format' },
  related_db: { name: 'Entry', invalid: 'Expected EMPIAR-#####, EMD-####, or PDB-####' },
};

function formatOkFor(kind: IdentifierKind, value: string): boolean {
  const v = value.trim();
  if (kind === 'orcid') return ORCID_RE.test(v) && orcidChecksumOk(v);
  if (kind === 'doi') return DOI_RE.test(v);
  return RELATED_DB_RE.test(v);
}

export function IdentifierField({
  kind,
  value,
  onChange,
  disabled = false,
  ...rest
}: {
  kind: IdentifierKind;
  value: string;
  onChange: (value: string) => void;
  disabled?: boolean;
} & Omit<TextFieldProps, 'value' | 'onChange' | 'error' | 'helperText'>) {
  const trimmed = value.trim();
  const debounced = useDebounced(trimmed, 400);
  const formatOk = formatOkFor(kind, value);

  const q = useIdentifierLookup(kind, debounced, formatOk && debounced.length > 0);

  const settled = formatOk && debounced === trimmed && !q.isFetching;
  const resolved = settled && !!q.data;
  const notFound = settled && !q.isError && q.data === null;
  const lookupError = settled && q.isError;

  let helperText: ReactNode = null;
  let isValid = false;
  if (trimmed) {
    if (!formatOk) helperText = LABELS[kind].invalid;
    else if (q.isFetching || debounced !== trimmed) helperText = 'Checking…';
    else if (resolved) {
      helperText = q.data?.label ?? '';
      isValid = true;
    } else if (lookupError) {
      helperText = 'valid format (lookup unavailable)';
      isValid = true;
    } else {
      helperText = `${LABELS[kind].name} not found`;
    }
  }
  const error = !!trimmed && (!formatOk || notFound);

  let helper: ReactNode;
  if (helperText == null) helper = undefined;
  else if (isValid) {
    helper = (
      <Box component="span" sx={{ display: 'inline-flex', alignItems: 'center', gap: 0.5 }}>
        <Icon sdsIcon="Check" sdsSize="xxs" color="green" />
        {helperText}
      </Box>
    );
  } else helper = helperText;

  return (
    <TextField
      value={value}
      onChange={(e) => onChange(kind === 'doi' ? normalizeDoi(e.target.value) : e.target.value)}
      disabled={disabled}
      error={error}
      helperText={helper}
      FormHelperTextProps={{ component: 'div', sx: isValid ? { color: 'success.main' } : undefined }}
      {...rest}
    />
  );
}
