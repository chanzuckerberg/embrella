'use client';

import { type ReactNode, useState } from 'react';
import { Icon } from '@czi-sds/components';
import OpenInNewIcon from '@mui/icons-material/OpenInNew';
import { Autocomplete, Box, Chip, Link, Stack, TextField } from '@mui/material';

import { useDebounced } from '../../../hooks/useDebounced';
import { useOntologySearch, useOntologyTerm } from '../../../hooks/useOntology';
import type { OntologyTerm } from '../../../services/ols';
import { OntologyOption } from './OntologyOption';
import { SectionCard } from './SectionCard';

const NCBITAXON = 'ncbitaxon';

function taxidFromOboId(oboId: string): number | null {
  const m = oboId.match(/^NCBITaxon:(\d+)$/i);
  return m ? Number(m[1]) : null;
}

export function Organism({
  organismName,
  organismTaxid,
  onChangeOrganismName,
  onChangeOrganismTaxid,
  readOnly,
  innerRef,
}: {
  organismName: string;
  organismTaxid: number | null;
  onChangeOrganismName: (value: string) => void;
  onChangeOrganismTaxid: (value: number | null) => void;
  readOnly: boolean;
  innerRef: (el: HTMLDivElement | null) => void;
}) {
  const [query, setQuery] = useState(organismName);
  const debouncedQuery = useDebounced(query, 400);

  const MIN_CHARS = 3;
  const searchTerm = debouncedQuery.trim().length >= MIN_CHARS ? debouncedQuery : '';
  const { data: options = [], isFetching, isError: searchError } = useOntologySearch(searchTerm, NCBITAXON);

  const taxidStr = organismTaxid != null ? `NCBITaxon:${organismTaxid}` : '';
  const debouncedTaxid = useDebounced(taxidStr, 400);
  const { data: resolved, isFetching: validating, isError: lookupError } = useOntologyTerm(debouncedTaxid, NCBITAXON);

  const taxidSet = organismTaxid != null;
  const taxidResolved = !!resolved && resolved.id.toLowerCase() === taxidStr.toLowerCase();

  let taxidHelper: ReactNode = ' ';
  if (taxidSet) {
    if (validating || debouncedTaxid !== taxidStr) taxidHelper = 'Checking…';
    else if (taxidResolved) taxidHelper = resolved?.label ?? '';
    else if (lookupError) taxidHelper = 'lookup unavailable';
    else taxidHelper = 'Tax ID not found';
  }
  const taxidError = taxidSet && !validating && debouncedTaxid === taxidStr && !lookupError && !taxidResolved;
  const taxidValid = taxidSet && (taxidResolved || lookupError);

  let noOptionsText = 'No matches';
  if (query.trim().length < MIN_CHARS) noOptionsText = `Type ${MIN_CHARS}+ characters to search`;
  else if (searchError) noOptionsText = 'Ontology lookup unavailable';

  return (
    <SectionCard title="Organism" sectionKey="organism" innerRef={innerRef}>
      <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2} alignItems={{ sm: 'flex-start' }}>
        <Autocomplete
          sx={{ flex: 1 }}
          freeSolo
          disabled={readOnly}
          loading={isFetching}
          options={options}
          noOptionsText={noOptionsText}
          filterOptions={(x) => x}
          getOptionLabel={(o) => (typeof o === 'string' ? o : o.label)}
          inputValue={query}
          onInputChange={(_, v) => {
            setQuery(v);
            onChangeOrganismName(v);
          }}
          onChange={(_, val) => {
            if (val && typeof val !== 'string') {
              onChangeOrganismName(val.label);
              const taxid = taxidFromOboId(val.id);
              if (taxid != null) onChangeOrganismTaxid(taxid);
            }
          }}
          renderOption={(props, o: OntologyTerm) => (
            <Box component="li" {...props} key={o.id}>
              <OntologyOption term={o} />
            </Box>
          )}
          renderInput={(params) => <TextField {...params} label="Organism name" size="small" />}
        />
        <Box sx={{ display: 'flex', alignItems: 'center', minHeight: { sm: 40 } }}>
          <Chip label="NCBI" size="small" />
        </Box>
        <TextField
          label="NCBI tax ID"
          required
          value={organismTaxid ?? ''}
          onChange={(e) => onChangeOrganismTaxid(e.target.value === '' ? null : Number(e.target.value))}
          size="small"
          sx={{ flex: 1 }}
          disabled={readOnly}
          error={taxidError}
          helperText={
            taxidValid ? (
              <Box component="span" sx={{ display: 'inline-flex', alignItems: 'flex-start', gap: 0.5 }}>
                <Box component="span" sx={{ display: 'inline-flex', mt: '2px' }}>
                  <Icon sdsIcon="Check" sdsSize="xxs" color="green" />
                </Box>
                {taxidHelper}
              </Box>
            ) : (
              taxidHelper
            )
          }
          FormHelperTextProps={{ component: 'div', sx: taxidValid ? { color: 'success.main' } : undefined }}
        />
        <Box sx={{ display: 'flex', alignItems: 'center', minHeight: { sm: 40 } }}>
          <Link
            href="https://www.ncbi.nlm.nih.gov/taxonomy"
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
            NCBI Taxonomy <OpenInNewIcon sx={{ fontSize: 14 }} />
          </Link>
        </Box>
      </Stack>
    </SectionCard>
  );
}
