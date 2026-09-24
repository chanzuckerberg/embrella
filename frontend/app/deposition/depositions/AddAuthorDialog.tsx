'use client';

import { useRef, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Icon } from '@czi-sds/components';
import { Autocomplete, Box, Button, IconButton, Link, Stack, TextField, Typography } from '@mui/material';

import { BaseFormDialog } from '@app/common/components/Forms/BaseFormDialog';
import { IdentifierField } from '../components/IdentifierField';
import { createPerson, searchPeople } from '../services/depositionApi';
import { ORCID_RE, orcidChecksumOk } from '../services/identifiers';
import type { Person } from '../types';
import { personName } from '../components/authorHelpers';

type Mode = 'search' | 'create';

export function AddAuthorDialog({
  open,
  onClose,
  existingIds,
  onAdd,
}: {
  open: boolean;
  onClose: () => void;
  existingIds: number[];
  onAdd: (personId: number) => void;
}) {
  const queryClient = useQueryClient();
  const [mode, setMode] = useState<Mode>('search');
  const [picked, setPicked] = useState<Person | null>(null);
  const [term, setTerm] = useState('');
  const [input, setInput] = useState('');
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [givenName, setGivenName] = useState('');
  const [familyName, setFamilyName] = useState('');
  const [orcid, setOrcid] = useState('');
  const [email, setEmail] = useState('');

  const { data: results, isFetching } = useQuery<Person[]>({
    queryKey: ['people', 'search', term],
    queryFn: () => searchPeople(term),
    enabled: term.trim().length >= 2,
  });
  const options = (results ?? []).filter((p) => !existingIds.includes(p.id));

  const onInput = (value: string) => {
    if (timer.current) clearTimeout(timer.current);
    timer.current = setTimeout(() => setTerm(value), 300);
  };

  const clearSearch = () => {
    if (timer.current) clearTimeout(timer.current);
    setInput('');
    setTerm('');
    setPicked(null);
  };

  const create = useMutation({
    mutationFn: () =>
      createPerson({
        given_name: givenName.trim(),
        family_name: familyName.trim(),
        orcid: orcid.trim() || null,
        contact_email: email.trim() || undefined,
      }),
    onSuccess: (person) => {
      queryClient.invalidateQueries({ queryKey: ['people'] });
      onAdd(person.id);
      handleClose();
    },
  });

  const reset = () => {
    if (timer.current) clearTimeout(timer.current);
    setMode('search');
    setPicked(null);
    setTerm('');
    setInput('');
    setGivenName('');
    setFamilyName('');
    setOrcid('');
    setEmail('');
    create.reset();
  };
  const handleClose = () => {
    reset();
    onClose();
  };

  const orcidTrimmed = orcid.trim();
  const orcidOk = orcidTrimmed === '' || (ORCID_RE.test(orcidTrimmed) && orcidChecksumOk(orcidTrimmed));
  const canSave =
    !create.isPending &&
    (mode === 'search' ? picked !== null : orcidOk && givenName.trim() !== '' && familyName.trim() !== '');

  const handleSave = () => {
    if (mode === 'search') {
      if (picked) {
        onAdd(picked.id);
        handleClose();
      }
      return;
    }
    create.mutate();
  };

  return (
    <BaseFormDialog
      open={open}
      onClose={handleClose}
      sdsSize="xs"
      title="Add author"
      saveButtonText="Add"
      isSubmitting={create.isPending}
      disabled={!canSave}
      onSave={handleSave}
    >
      {mode === 'search' ? (
        <Box>
          <Typography variant="subtitle2" sx={{ fontWeight: 700, mb: 0.75 }}>
            Search the directory
          </Typography>

          {picked ? (
            <Box
              sx={{
                border: '1px solid',
                borderColor: 'divider',
                borderRadius: 1,
                p: 1.5,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                gap: 1,
              }}
            >
              <Box sx={{ minWidth: 0 }}>
                <Typography variant="body2" sx={{ fontWeight: 600 }} noWrap>
                  {personName(picked)}
                </Typography>
                {picked.orcid && (
                  <Typography variant="caption" color="text.secondary">
                    {picked.orcid}
                  </Typography>
                )}
              </Box>
              <Button size="small" onClick={clearSearch} disabled={create.isPending}>
                Change
              </Button>
            </Box>
          ) : (
            <>
              <Autocomplete
                options={options}
                getOptionLabel={personName}
                isOptionEqualToValue={(a, b) => a.id === b.id}
                value={picked}
                inputValue={input}
                loading={isFetching}
                filterOptions={(x) => x}
                onInputChange={(_, v, reason) => {
                  if (reason === 'clear') {
                    clearSearch();
                    return;
                  }
                  setInput(v);
                  onInput(v);
                }}
                onChange={(_, v) => setPicked(v)}
                noOptionsText={term.trim().length < 2 ? 'Type at least 2 characters…' : 'No matches'}
                renderInput={(params) => (
                  <TextField
                    {...params}
                    size="small"
                    placeholder="Search by name, email or ORCID"
                    InputProps={{
                      ...params.InputProps,
                      endAdornment: (
                        <>
                          {input && (
                            <IconButton size="small" aria-label="Clear search" onClick={clearSearch}>
                              <Icon sdsIcon="XMark" sdsSize="xs" color="gray" />
                            </IconButton>
                          )}
                          {params.InputProps.endAdornment}
                        </>
                      ),
                    }}
                  />
                )}
              />
              <Typography variant="body2" sx={{ mt: 1.5, color: 'text.secondary' }}>
                Not in the directory?{' '}
                <Link component="button" type="button" onClick={() => setMode('create')}>
                  Add a new author
                </Link>
              </Typography>
            </>
          )}
        </Box>
      ) : (
        <Box>
          <Stack direction="row" alignItems="center" justifyContent="space-between" sx={{ mb: 1 }}>
            <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>
              New author
            </Typography>
            <Link component="button" type="button" disabled={create.isPending} onClick={() => setMode('search')}>
              ← Back to directory search
            </Link>
          </Stack>

          <Stack spacing={2}>
            <Stack direction="row" spacing={2}>
              <TextField
                label="Given name"
                required
                value={givenName}
                onChange={(e) => setGivenName(e.target.value)}
                size="small"
                fullWidth
                disabled={create.isPending}
              />
              <TextField
                label="Family name"
                required
                value={familyName}
                onChange={(e) => setFamilyName(e.target.value)}
                size="small"
                fullWidth
                disabled={create.isPending}
              />
            </Stack>
            <IdentifierField
              kind="orcid"
              label="ORCID"
              placeholder="xxxx-xxxx-xxxx-xxxx"
              value={orcid}
              onChange={setOrcid}
              size="small"
              fullWidth
              disabled={create.isPending}
            />
            <TextField
              label="Email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              size="small"
              fullWidth
              disabled={create.isPending}
            />
          </Stack>

          {create.isError && (
            <Typography variant="body2" color="error.main" sx={{ mt: 1.5 }}>
              Could not add the author - check the ORCID format (xxxx-xxxx-xxxx-xxxx) and try again.
            </Typography>
          )}
        </Box>
      )}
    </BaseFormDialog>
  );
}
