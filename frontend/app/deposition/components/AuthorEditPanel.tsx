'use client';

import { forwardRef, useImperativeHandle, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Autocomplete, Avatar, Box, Checkbox, FormControlLabel, TextField, Typography } from '@mui/material';

import type { AuthorRef, Institution, Person } from '../types';
import { useDebounced } from '../hooks/useDebounced';
import { createInstitution, searchInstitutions, updatePerson } from '../services/depositionApi';
import { ORCID_RE, orcidChecksumOk } from '../services/identifiers';
import { IdentifierField } from './IdentifierField';
import { AVATAR_COLORS, initials, personName, RolePill, splitFullName } from './authorHelpers';

export type AuthorEditPanelHandle = { save: () => Promise<void> };

export const AuthorEditPanel = forwardRef<
  AuthorEditPanelHandle,
  {
    person?: Person;
    authorRef: AuthorRef;
    order: number;
    disabled: boolean;
    onToggle: (key: 'is_primary' | 'is_corresponding') => void;
  }
>(function AuthorEditPanel({ person, authorRef, order, disabled, onToggle }, ref) {
  const queryClient = useQueryClient();
  const name = personName(person);
  const [fullName, setFullName] = useState(name === 'Unknown author' ? '' : name);
  const [orcid, setOrcid] = useState(person?.orcid ?? '');
  const [institution, setInstitution] = useState<Institution | null>(person?.institution ?? null);
  const [institutionInput, setInstitutionInput] = useState(person?.institution?.name ?? '');

  const orcidTrimmed = orcid.trim();
  const orcidOk = orcidTrimmed === '' || (ORCID_RE.test(orcidTrimmed) && orcidChecksumOk(orcidTrimmed));
  const { given_name, family_name } = splitFullName(fullName);

  const debouncedInstitution = useDebounced(institutionInput.trim(), 300);
  const { data: institutionOptions = [] } = useQuery({
    queryKey: ['institutions', 'search', debouncedInstitution],
    queryFn: () => searchInstitutions(debouncedInstitution),
    enabled: !disabled && debouncedInstitution.length >= 1,
  });

  const affiliationName = (institution?.name ?? institutionInput).trim();
  const dirty =
    !!person &&
    (given_name !== (person.given_name ?? '') ||
      family_name !== (person.family_name ?? '') ||
      orcidTrimmed !== (person.orcid ?? '') ||
      affiliationName !== (person.institution?.name ?? ''));

  const saveMutation = useMutation({
    mutationFn: async () => {
      let institutionId: number | null = null;
      if (institution && institution.name === affiliationName) {
        institutionId = institution.id;
      } else if (affiliationName) {
        const matches = await searchInstitutions(affiliationName);
        const exact = matches.find((i) => i.name.toLowerCase() === affiliationName.toLowerCase());
        institutionId = exact ? exact.id : (await createInstitution(affiliationName)).id;
      }
      return updatePerson(authorRef.author_id, {
        given_name: given_name.trim(),
        family_name: family_name.trim(),
        orcid: orcidTrimmed || null,
        institution_id: institutionId,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['people', 'by-ids'] });
      queryClient.invalidateQueries({ queryKey: ['institutions'] });
    },
  });

  useImperativeHandle(
    ref,
    () => ({
      save: async () => {
        if (!disabled && dirty && orcidOk) await saveMutation.mutateAsync();
      },
    }),
    [disabled, dirty, orcidOk, saveMutation]
  );

  return (
    <Box
      sx={{
        border: '1px solid',
        borderColor: 'divider',
        borderRadius: 2,
        p: 2.5,
        pb: 3,
        bgcolor: 'grey.50',
      }}
    >
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.25 }}>
          <Avatar
            sx={{ width: 24, height: 24, fontSize: 11, bgcolor: AVATAR_COLORS[(order - 1) % AVATAR_COLORS.length] }}
          >
            {initials(name)}
          </Avatar>
          <Typography
            variant="body2"
            sx={{ fontWeight: 700, color: 'text.secondary', letterSpacing: 0.6, fontSize: '0.75rem' }}
          >
            AUTHOR {order}
          </Typography>
          {authorRef.is_primary && <RolePill kind="primary" />}
          {authorRef.is_corresponding && <RolePill kind="corresponding" />}
        </Box>
      </Box>

      <Box
        sx={{
          display: 'grid',
          gridTemplateColumns: { xs: '1fr', sm: '1fr 1fr' },
          gap: 2,
          mt: 5,
          mb: 2,
        }}
      >
        <TextField
          label="Full name"
          value={fullName}
          onChange={(e) => setFullName(e.target.value)}
          size="small"
          fullWidth
          disabled={disabled}
        />
        <Autocomplete
          freeSolo
          size="small"
          disabled={disabled}
          options={institutionOptions}
          value={institution}
          inputValue={institutionInput}
          getOptionLabel={(o) => (typeof o === 'string' ? o : o.name)}
          isOptionEqualToValue={(o, v) => o.id === v.id}
          filterOptions={(x) => x}
          onInputChange={(_, v) => {
            setInstitutionInput(v);
            if (institution && v !== institution.name) setInstitution(null);
          }}
          onChange={(_, val) => {
            if (val && typeof val !== 'string') {
              setInstitution(val);
              setInstitutionInput(val.name);
            } else {
              setInstitution(null);
            }
          }}
          renderInput={(params) => (
            <TextField {...params} label="Affiliation" placeholder="Search or add institution" fullWidth />
          )}
        />
      </Box>

      <Box
        sx={{
          display: 'flex',
          flexDirection: { xs: 'column', sm: 'row' },
          flexWrap: 'wrap',
          alignItems: { xs: 'stretch', sm: 'flex-start' },
          columnGap: { xs: 1.5, sm: 3 },
          rowGap: 1.5,
        }}
      >
        <IdentifierField
          kind="orcid"
          label="ORCID ID"
          value={orcid}
          onChange={setOrcid}
          placeholder="0000-0000-0000-0000"
          size="small"
          disabled={disabled}
          inputProps={{ 'aria-label': 'ORCID iD' }}
          sx={{ width: { xs: '100%', sm: 260 }, flexShrink: 0, mt: 3 }}
        />

        <Box
          sx={{
            display: 'flex',
            flexWrap: 'nowrap',
            alignItems: 'center',
            gap: 0.5,
            whiteSpace: 'nowrap',
            minHeight: { sm: 40 },
          }}
        >
          <FormControlLabel
            control={
              <Checkbox
                size="small"
                checked={authorRef.is_primary}
                onChange={() => onToggle('is_primary')}
                disabled={disabled}
              />
            }
            label="Primary author"
            sx={{ m: 0 }}
          />
          <FormControlLabel
            control={
              <Checkbox
                size="small"
                checked={authorRef.is_corresponding}
                onChange={() => onToggle('is_corresponding')}
                disabled={disabled}
              />
            }
            label="Corresponding author"
            sx={{ m: 0 }}
          />
        </Box>
      </Box>
    </Box>
  );
});
