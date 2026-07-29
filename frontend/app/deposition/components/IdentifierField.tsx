'use client';

import { useState } from 'react';
import { TextField, type TextFieldProps } from '@mui/material';

import { useIdentifierLookup } from '../hooks/useIdentifier';
import { DOI_RE, ORCID_RE, orcidChecksumOk, RELATED_DB_RE, type IdentifierKind } from '../services/identifiers';

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
  const [committed, setCommitted] = useState('');
  const formatOk = formatOkFor(kind, value);

  const q = useIdentifierLookup(kind, committed, committed !== '' && formatOk);

  const checked = trimmed !== '' && committed === trimmed;
  const settled = checked && !q.isFetching;
  const resolved = settled && !!q.data;
  const notFound = settled && !q.isError && q.data === null;
  const lookupError = settled && q.isError;

  let helperText = ' ';
  let isValid = false;
  if (trimmed && !formatOk) {
    helperText = LABELS[kind].invalid;
  } else if (checked) {
    if (q.isFetching) helperText = 'Checking…';
    else if (resolved) {
      helperText = `✓ ${q.data?.label ?? ''}`;
      isValid = true;
    } else if (lookupError) {
      helperText = '✓ valid format (lookup unavailable)';
      isValid = true;
    } else {
      helperText = `${LABELS[kind].name} not found`;
    }
  }
  const error = !!trimmed && (!formatOk || notFound);

  return (
    <TextField
      value={value}
      onChange={(e) => onChange(e.target.value)}
      onBlur={() => setCommitted(trimmed)}
      disabled={disabled}
      error={error}
      helperText={helperText}
      FormHelperTextProps={{ sx: isValid ? { color: 'success.main' } : undefined }}
      {...rest}
    />
  );
}
