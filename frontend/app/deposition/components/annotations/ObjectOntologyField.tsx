'use client';

import { type ReactNode, useMemo, useState } from 'react';
import {
  Autocomplete,
  Box,
  CircularProgress,
  MenuItem,
  Stack,
  type SxProps,
  TextField,
  type Theme,
  Typography,
} from '@mui/material';

import { useDebounced } from '../../hooks/useDebounced';
import { useOntologySearch, useOntologyTerm } from '../../hooks/useOntology';
import { GO_CELLULAR_COMPONENT_IRI, type OntologyTerm } from '../../services/ols';
import type { DepositionAnnotation } from '../../types';
import { OntologyOption } from '../OntologyOption';

interface ObjectOntology {
  type: string;
  ontology: string;
  pattern: string;
  prefix: string;
  separator?: string; // only for detecting an existing id's prefix (EMD-, PDB-); ':' otherwise
  manualOnly?: boolean;
  childrenOf?: string;
  placeholder?: string;
}

const OBJECT_ONTOLOGIES: ObjectOntology[] = [
  {
    type: 'GO',
    ontology: 'go',
    pattern: '^GO:[0-9]{7}$',
    prefix: 'GO',
    childrenOf: GO_CELLULAR_COMPONENT_IRI,
  },
  { type: 'UBERON', ontology: 'uberon', pattern: '^UBERON:[0-9]{7}$', prefix: 'UBERON' },
  { type: 'CHEBI', ontology: 'chebi', pattern: '^CHEBI:[0-9]+$', prefix: 'CHEBI' },
  {
    type: 'UniProtKB',
    ontology: '',
    pattern: '^UniProtKB:(?:[OPQ][0-9][A-Z0-9]{3}[0-9]|[A-NR-Z][0-9](?:[A-Z][A-Z0-9]{2}[0-9]){1,2})$',
    prefix: 'UniProtKB',
    manualOnly: true,
    placeholder: 'UniProtKB:P12345',
  },
  {
    type: 'CDPO',
    ontology: '',
    pattern: '^CDPO:[0-9]{7}$',
    prefix: 'CDPO',
    manualOnly: true,
    placeholder: 'CDPO:0000001',
  },
  {
    type: 'EMDB',
    ontology: '',
    pattern: '^EMD-[0-9]{4,5}$',
    prefix: 'EMD',
    separator: '-',
    manualOnly: true,
    placeholder: 'EMD-1234',
  },
  {
    type: 'PDB',
    ontology: '',
    pattern: '^PDB-[0-9a-zA-Z]{4,8}$',
    prefix: 'PDB',
    separator: '-',
    manualOnly: true,
    placeholder: 'PDB-4hhb',
  },
];

export function ObjectOntologyField({
  name,
  id,
  onChange,
  disabled,
  sx,
}: {
  name: string;
  id: string;
  onChange: (patch: Partial<DepositionAnnotation>) => void;
  disabled?: boolean;
  sx?: SxProps<Theme>;
}) {
  const inferred = OBJECT_ONTOLOGIES.find((o) => id.startsWith(`${o.prefix}${o.separator ?? ':'}`)) ?? null;
  const [picked, setPicked] = useState<ObjectOntology | null>(null);
  const cfg = picked ?? inferred;
  const lockOntology = () => {
    if (!picked && inferred) setPicked(inferred);
  };
  const [ontologyTouched, setOntologyTouched] = useState(false);
  const [query, setQuery] = useState(id);
  const debounced = useDebounced(query, 300);
  const searchable = !!cfg && !cfg.manualOnly;
  const { data: options = [], isFetching } = useOntologySearch(
    debounced,
    cfg?.ontology ?? '',
    searchable,
    cfg?.childrenOf
  );
  const {
    data: resolved,
    isFetching: validating,
    isError: lookupError,
  } = useOntologyTerm(id, cfg?.ontology ?? '', searchable);
  const formatOk = !!cfg && new RegExp(cfg.pattern).test(id.trim());
  const idResolved = !!resolved && resolved.id.toLowerCase() === id.trim().toLowerCase();

  const selectedValue = useMemo<OntologyTerm | null>(() => {
    if (!id.trim()) return null;
    return idResolved && resolved ? resolved : { id, label: id, synonyms: [] };
  }, [id, idResolved, resolved]);

  const selectType = (type: string) => {
    setPicked(OBJECT_ONTOLOGIES.find((o) => o.type === type) ?? null);
    setQuery('');
    onChange({ object_id: '' });
  };

  const nameEmpty = !name.trim();
  let nameHelper = ' ';
  if (!disabled && nameEmpty) nameHelper = 'Name is required; pick an ID below.';
  else if (!disabled && !id.trim()) nameHelper = 'Edit if needed.';

  let idField: ReactNode;
  if (!cfg) {
    idField = (
      <TextField
        label="Object ID"
        required
        size="small"
        fullWidth
        disabled
        placeholder="Choose an ontology first"
        helperText="Search unlocks after picking an ontology."
      />
    );
  } else if (searchable) {
    const idPattern = new RegExp(cfg.pattern);
    let idHelper = `Search ${cfg.type} by name, or paste an ID.`;
    let idError = false;
    if (id.trim()) {
      if (!formatOk) {
        idHelper = `Invalid ID format for ${cfg.type}.`;
        idError = true;
      } else if (validating) {
        idHelper = 'Checking…';
      } else if (idResolved) {
        idHelper = `${resolved?.label ?? id} · ${id}`;
      } else if (lookupError) {
        idHelper = 'Valid format · lookup unavailable';
      } else {
        idHelper = 'ID not found';
        idError = true;
      }
    }
    idField = (
      <Autocomplete<OntologyTerm, false, false, true>
        freeSolo
        options={options}
        loading={isFetching}
        filterOptions={(x) => x}
        getOptionLabel={(o) => (typeof o === 'string' ? o : `${o.label} (${o.id})`)}
        isOptionEqualToValue={(a, b) => a.id === b.id}
        value={selectedValue}
        inputValue={query || id}
        onInputChange={(_, v, reason) => {
          if (reason === 'reset') return;
          lockOntology();
          setQuery(v);
          onChange({ object_id: idPattern.test(v.trim()) ? v.trim() : '' });
        }}
        onChange={(_, val) => {
          if (val && typeof val !== 'string') {
            setQuery(val.id);
            onChange(name.trim() ? { object_id: val.id } : { object_id: val.id, object_name: val.label });
          }
        }}
        disabled={disabled}
        renderOption={(props, o: OntologyTerm) => (
          <Box component="li" {...props} key={o.id}>
            <OntologyOption term={o} />
          </Box>
        )}
        renderInput={(params) => (
          <TextField
            {...params}
            label="Object ID"
            required
            size="small"
            error={idError}
            placeholder={`Search ${cfg.type} by name, or paste ID`}
            helperText={idHelper}
            InputProps={{
              ...params.InputProps,
              endAdornment: (
                <>
                  {isFetching ? <CircularProgress size={16} /> : null}
                  {params.InputProps.endAdornment}
                </>
              ),
            }}
          />
        )}
      />
    );
  } else {
    idField = (
      <TextField
        label="Object ID"
        required
        size="small"
        fullWidth
        value={id}
        onChange={(e) => {
          lockOntology();
          onChange({ object_id: e.target.value.trim() });
        }}
        disabled={disabled}
        placeholder={cfg.placeholder}
        error={!!id.trim() && !formatOk}
        helperText={!!id.trim() && !formatOk ? `Expected format like ${cfg.placeholder}` : `Enter the ${cfg.type} ID.`}
      />
    );
  }

  return (
    <Stack direction={{ xs: 'column', md: 'row' }} spacing={2} alignItems={{ md: 'flex-start' }} sx={sx}>
      <TextField
        select
        size="small"
        label="Ontology"
        required
        value={cfg?.type ?? ''}
        onChange={(e) => selectType(e.target.value)}
        disabled={disabled}
        onBlur={() => setOntologyTouched(true)}
        error={!disabled && !cfg && ontologyTouched}
        helperText={!cfg && !disabled ? 'Required - choose the ontology this object belongs to.' : ' '}
        InputLabelProps={{ shrink: true }}
        SelectProps={{
          displayEmpty: true,
          renderValue: (v) =>
            (v as string) || (
              <Typography component="span" color="text.disabled">
                Select ontology
              </Typography>
            ),
        }}
        sx={{ width: 200, flexShrink: 0 }}
      >
        {OBJECT_ONTOLOGIES.map((o) => (
          <MenuItem key={o.type} value={o.type}>
            {o.type}
          </MenuItem>
        ))}
      </TextField>

      <TextField
        label="Object name"
        required
        size="small"
        sx={{ flex: 1, minWidth: 0 }}
        value={name}
        onChange={(e) => onChange({ object_name: e.target.value })}
        disabled={disabled}
        error={!disabled && nameEmpty}
        helperText={nameHelper}
      />

      <Box sx={{ flex: 1, minWidth: 0 }}>{idField}</Box>
    </Stack>
  );
}
