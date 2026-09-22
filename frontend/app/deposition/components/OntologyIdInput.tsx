'use client';

import { useState } from 'react';
import { Icon } from '@czi-sds/components';
import OpenInNewIcon from '@mui/icons-material/OpenInNew';
import { Autocomplete, Box, Chip, Link, Stack, TextField } from '@mui/material';

import { useDebounced } from '../hooks/useDebounced';
import { useOntologySearch, useOntologyTerm } from '../hooks/useOntology';
import type { OntologyTerm } from '../services/ols';
import { OntologyOption } from './OntologyOption';

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
  required = false,
  childrenOf,
  prefixInValue = true,
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
  required?: boolean;
  childrenOf?: string; // restrict suggestions to descendants
  prefixInValue?: boolean;
}) {
  const [query, setQuery] = useState(name);
  const debouncedQuery = useDebounced(query, 300);
  const debouncedId = useDebounced(id, 400);
  const olsEnabled = !manualOnly;

  const idInputValue = prefixInValue || !id.startsWith(`${prefix}:`) ? id : id.slice(prefix.length + 1);
  const handleIdChange = (raw: string) => {
    if (prefixInValue) {
      onChange({ id: raw });
      return;
    }
    const bare = raw.trim().replace(new RegExp(`^${prefix}:`), '');
    onChange({ id: bare ? `${prefix}:${bare}` : '' });
  };

  const {
    data: options = [],
    isFetching,
    isError: searchError,
  } = useOntologySearch(debouncedQuery, ontology, olsEnabled, childrenOf);
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

  const requiredMissing = required && !idSet;
  let idHelper = ' ';
  if (requiredMissing) {
    idHelper = 'Required';
  } else if (idSet) {
    if (!formatOk) idHelper = 'Invalid ID format for this field';
    else if (!isOlsPrefix) idHelper = 'valid format';
    else if (validating || debouncedId !== id) idHelper = 'Checking…';
    else if (idResolved) idHelper = resolved?.label ?? '';
    else if (lookupError) idHelper = 'valid format (lookup unavailable)';
    else idHelper = 'ID not found';
  }
  const idError =
    requiredMissing ||
    (idSet && (!formatOk || (isOlsPrefix && !validating && debouncedId === id && !lookupError && !idResolved)));

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
          required={required}
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
          onInputChange={(_, v, reason) => {
            setQuery(v);
            if (reason === 'clear') onChange({ name: '', id: '' });
            else onChange({ name: v });
          }}
          onChange={(_, val) => {
            if (val && typeof val !== 'string') onChange({ name: val.label, id: val.id });
          }}
          renderOption={(props, o: OntologyTerm) => (
            <Box component="li" {...props} key={o.id}>
              <OntologyOption term={o} />
            </Box>
          )}
          renderInput={(params) => <TextField {...params} label={`${label} name`} size="small" required={required} />}
        />
      )}
      <Box sx={{ display: 'flex', alignItems: 'center', minHeight: { sm: 40 } }}>
        <Chip label={prefix} size="small" />
      </Box>
      <TextField
        label={`${label} ID`}
        value={idInputValue}
        onChange={(e) => handleIdChange(e.target.value)}
        placeholder={idPlaceholder}
        size="small"
        sx={{ flex: 1 }}
        disabled={disabled}
        required={required}
        error={idError}
        helperText={
          idValid ? (
            <Box component="span" sx={{ display: 'inline-flex', alignItems: 'flex-start', gap: 0.5 }}>
              <Box component="span" sx={{ display: 'inline-flex', mt: '2px' }}>
                <Icon sdsIcon="Check" sdsSize="xxs" color="green" />
              </Box>
              {idHelper}
            </Box>
          ) : (
            idHelper
          )
        }
        FormHelperTextProps={{ component: 'div', sx: idValid ? { color: 'success.main' } : undefined }}
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
