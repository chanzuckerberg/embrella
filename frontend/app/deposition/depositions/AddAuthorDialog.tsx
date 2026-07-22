'use client';

import { useRef, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Autocomplete, Box, Divider, Stack, TextField, Typography } from '@mui/material';

import { BaseFormDialog } from '@app/common/components/Forms/BaseFormDialog';
import { createPerson, searchPeople } from '../services/depositionApi';
import type { Person } from '../types';

const personName = (p: Person) => `${p.given_name} ${p.family_name}`.trim();

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
  const [picked, setPicked] = useState<Person | null>(null);
  const [term, setTerm] = useState('');
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

  // Debounce the typed term (in the input handler, not an effect).
  const onInput = (value: string) => {
    if (timer.current) clearTimeout(timer.current);
    timer.current = setTimeout(() => setTerm(value), 300);
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
      onClose();
    },
  });

  const creatingNew = picked === null && (givenName.trim() !== '' || familyName.trim() !== '');
  const canSave =
    !create.isPending && (picked !== null || (givenName.trim() !== '' && familyName.trim() !== ''));

  const handleSave = () => {
    if (picked) {
      onAdd(picked.id);
      onClose();
      return;
    }
    create.mutate();
  };

  return (
    <BaseFormDialog
      open={open}
      onClose={onClose}
      sdsSize="xs"
      title="Add author"
      saveButtonText="Add"
      isSubmitting={create.isPending}
      disabled={!canSave}
      onSave={handleSave}
    >
      <Box>
        <Typography variant="subtitle2" sx={{ fontWeight: 700, mb: 0.75 }}>
          Add from directory
        </Typography>
        <Autocomplete
          options={options}
          getOptionLabel={personName}
          isOptionEqualToValue={(a, b) => a.id === b.id}
          value={picked}
          loading={isFetching}
          filterOptions={(x) => x}
          disabled={create.isPending}
          onInputChange={(_, v) => onInput(v)}
          onChange={(_, v) => setPicked(v)}
          noOptionsText={term.trim().length < 2 ? 'Type at least 2 characters…' : 'No matches'}
          renderInput={(params) => <TextField {...params} size="small" placeholder="Search people…" />}
        />
      </Box>

      <Divider>or add a new author</Divider>

      <Stack spacing={2}>
        <Stack direction="row" spacing={2}>
          <TextField
            label="Given name"
            value={givenName}
            onChange={(e) => setGivenName(e.target.value)}
            size="small"
            fullWidth
            disabled={picked !== null || create.isPending}
          />
          <TextField
            label="Family name"
            value={familyName}
            onChange={(e) => setFamilyName(e.target.value)}
            size="small"
            fullWidth
            disabled={picked !== null || create.isPending}
          />
        </Stack>
        <TextField
          label="ORCID"
          placeholder="xxxx-xxxx-xxxx-xxxx"
          value={orcid}
          onChange={(e) => setOrcid(e.target.value)}
          size="small"
          fullWidth
          disabled={picked !== null || create.isPending}
        />
        <TextField
          label="Email"
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          size="small"
          fullWidth
          disabled={picked !== null || create.isPending}
        />
      </Stack>

      {creatingNew && (
        <Typography variant="caption" color="text.secondary">
          A new directory entry will be created.
        </Typography>
      )}
      {create.isError && (
        <Typography variant="body2" color="error.main">
          Could not add the author — check the ORCID format (xxxx-xxxx-xxxx-xxxx) and try again.
        </Typography>
      )}
    </BaseFormDialog>
  );
}
