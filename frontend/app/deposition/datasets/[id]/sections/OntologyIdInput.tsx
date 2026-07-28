'use client';

import { useEffect, useState } from 'react';
import OpenInNewIcon from '@mui/icons-material/OpenInNew';
import { Autocomplete, Box, Chip, Link, Stack, TextField, Typography } from '@mui/material';

import { useOntologySearch, useOntologyTerm } from '../../../hooks/useOntology';
import type { OntologyTerm } from '../../../services/ols';

function useDebounced<T>(value: T, ms: number): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setDebounced(value), ms);
    return () => clearTimeout(t);
  }, [value, ms]);
  return debounced;
}

export function OntologyIdInput({
  label,
  ontology,
  pattern,
  prefix,
  lookup,
  name,
  id,
  onChange,
  disabled = false,
  manualOnly = false,
  idPlaceholder,
}: {
  label: string;
  ontology: string;
  pattern: string; // portal id-format regex
  prefix: string;
  lookup: string;
  name: string;
  id: string;
  onChange: (patch: { name?: string; id?: string }) => void;
  disabled?: boolean;
  manualOnly?: boolean;
  idPlaceholder?: string;
}) {
  const [query, setQuery] = useState(name);
  const debouncedQuery = useDebounced(query, 300);
  const debouncedId = useDebounced(id, 400);
  const olsEnabled = !manualOnly;

  const {
    data: options = [],
    isFetching,
    isError: searchError,
  } = useOntologySearch(debouncedQuery, ontology, olsEnabled);
  const {
    data: resolved,
    isFetching: validating,
    isError: lookupError,
  } = useOntologyTerm(debouncedId, ontology, olsEnabled);

  const trimmedId = id.trim();
  const idSet = trimmedId.length > 0;
  const formatOk = new RegExp(pattern).test(trimmedId);
  const idPrefix = trimmedId.match(/^[A-Za-z]+/)?.[0]?.toLowerCase() ?? '';
  const isOlsPrefix = olsEnabled && ontology.toLowerCase().split(',').includes(idPrefix);
  const idResolved = !!resolved && resolved.id.toLowerCase() === trimmedId.toLowerCase();
  const idValid = formatOk && (isOlsPrefix ? idResolved || lookupError : true);

  let idHelper = ' ';
  if (idSet) {
    if (!formatOk) idHelper = 'Invalid ID format for this field';
    else if (!isOlsPrefix) idHelper = '✓ valid format';
    else if (validating || debouncedId !== id) idHelper = 'Checking…';
    else if (idResolved) idHelper = `✓ ${resolved?.label ?? ''}`;
    else if (lookupError) idHelper = '✓ valid format (lookup unavailable)';
    else idHelper = 'ID not found';
  }
  const idError =
    idSet && (!formatOk || (isOlsPrefix && !validating && debouncedId === id && !lookupError && !idResolved));

  return (
    <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2} alignItems={{ sm: 'flex-start' }}>
      {manualOnly ? (
        <TextField
          label={`${label} name`}
          value={name}
          onChange={(e) => onChange({ name: e.target.value })}
          size="small"
          sx={{ flex: 1 }}
          disabled={disabled}
        />
      ) : (
        <Autocomplete
          sx={{ flex: 1 }}
          freeSolo
          disabled={disabled}
          loading={isFetching}
          options={options}
          noOptionsText={searchError ? 'Ontology lookup unavailable' : 'No matches'}
          filterOptions={(x) => x}
          getOptionLabel={(o) => (typeof o === 'string' ? o : o.label)}
          inputValue={query}
          onInputChange={(_, v) => {
            setQuery(v);
            onChange({ name: v });
          }}
          onChange={(_, val) => {
            if (val && typeof val !== 'string') onChange({ name: val.label, id: val.id });
          }}
          renderOption={(props, o: OntologyTerm) => (
            <Box component="li" {...props} key={o.id}>
              <Box>
                <Typography variant="body2">
                  {o.label}{' '}
                  <Typography
                    component="span"
                    variant="caption"
                    color="text.secondary"
                    sx={{ fontFamily: 'monospace' }}
                  >
                    {o.id}
                  </Typography>
                </Typography>
                {o.synonyms.length > 0 && (
                  <Typography variant="caption" color="text.secondary">
                    syn: {o.synonyms.slice(0, 3).join(', ')}
                  </Typography>
                )}
              </Box>
            </Box>
          )}
          renderInput={(params) => <TextField {...params} label={`${label} name`} size="small" />}
        />
      )}
      <Box sx={{ display: 'flex', alignItems: 'center', minHeight: { sm: 40 } }}>
        <Chip label={prefix} size="small" />
      </Box>
      <TextField
        label={`${label} ID`}
        value={id}
        onChange={(e) => onChange({ id: e.target.value })}
        placeholder={idPlaceholder}
        size="small"
        sx={{ flex: 1 }}
        disabled={disabled}
        error={idError}
        helperText={idHelper}
        FormHelperTextProps={{ sx: idValid ? { color: 'success.main' } : undefined }}
      />
      <Box sx={{ display: 'flex', alignItems: 'center', minHeight: { sm: 35 } }}>
        <Link
          href={lookup}
          target="_blank"
          rel="noopener"
          variant="body2"
          sx={{
            whiteSpace: 'nowrap',
            display: 'inline-flex',
            alignItems: 'center',
            gap: 0.25,
            fontWeight: 600,
          }}
        >
          {prefix} lookup <OpenInNewIcon sx={{ fontSize: 14 }} />
        </Link>
      </Box>
    </Stack>
  );
}
