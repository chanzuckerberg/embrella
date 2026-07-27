'use client';

import { useCallback, useEffect, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { Button } from '@czi-sds/components';
import { Box, Divider, Paper, Stack, TextField, Typography } from '@mui/material';

import { updateDeposition } from '../services/depositionApi';
import { depositionKeys } from '../queryKeys';
import type { AuthorRef, CrossRef, Deposition } from '../types';
import { type AutoSaveState, useDraftAutoSave } from '../hooks/useDraftAutoSave';
import { CrossReferencesEditor } from './CrossReferencesEditor';
import { AuthorTable } from './AuthorTable';

interface FormState {
  title: string;
  description: string;
  crossRefs: CrossRef[];
  authors: AuthorRef[];
}

const split = (s?: string): string[] =>
  (s ?? '')
    .split(',')
    .map((v) => v.trim())
    .filter(Boolean);

function toForm(d: Deposition): FormState {
  return {
    title: d.title ?? '',
    description: d.description ?? '',
    crossRefs: [
      ...split(d.deposition_publications).map((value): CrossRef => ({ type: 'publication', value })),
      ...split(d.related_database_entries).map((value): CrossRef => ({ type: 'related_db', value })),
    ],
    authors: d.authors_json ?? [],
  };
}

export function DepositionForm({
  deposition,
  reportSave,
  readOnly = false,
}: {
  deposition: Deposition;
  reportSave?: (state: AutoSaveState) => void;
  readOnly?: boolean;
}) {
  const queryClient = useQueryClient();
  const [form, setForm] = useState<FormState>(() => toForm(deposition));

  const save = useCallback(
    async (payload: FormState) => {
      const publications = payload.crossRefs.filter((r) => r.type === 'publication').map((r) => r.value.trim());
      const related = payload.crossRefs.filter((r) => r.type === 'related_db').map((r) => r.value.trim());
      const updated = await updateDeposition(deposition.id, {
        title: payload.title,
        description: payload.description,
        deposition_publications: publications.filter(Boolean).join(', '),
        related_database_entries: related.filter(Boolean).join(', '),
        authors_json: payload.authors,
      });
      queryClient.setQueryData(depositionKeys.deposition(deposition.id), updated);
      queryClient.invalidateQueries({ queryKey: [...depositionKeys.all, 'submissions'] });
    },
    [deposition.id, queryClient]
  );

  const { status, lastSavedAt, saveNow } = useDraftAutoSave(form, save, { enabled: !readOnly });

  useEffect(() => {
    reportSave?.({ status, lastSavedAt, saveNow });
  }, [status, lastSavedAt, saveNow, reportSave]);

  const set = <K extends keyof FormState>(key: K, value: FormState[K]) =>
    setForm((prev) => ({ ...prev, [key]: value }));

  return (
    <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: '1fr 1fr' }, gap: 3 }}>
      <Paper variant="outlined" sx={{ p: 3, borderRadius: 2 }}>
        <Typography variant="h6" sx={{ fontWeight: 700, mb: 6 }}>
          Basic
        </Typography>
        <Stack spacing={6}>
          <TextField
            label="Title"
            value={form.title}
            onChange={(e) => set('title', e.target.value)}
            required
            fullWidth
            size="small"
            disabled={readOnly}
          />
          <TextField
            label="Description"
            value={form.description}
            onChange={(e) => set('description', e.target.value)}
            multiline
            minRows={5}
            fullWidth
            size="small"
            disabled={readOnly}
            helperText="3–5 sentences."
            sx={{ '& textarea': { resize: 'vertical' } }}
          />
        </Stack>

        <Divider sx={{ my: 3 }} />

        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1.5 }}>
          <Typography variant="h6" sx={{ fontWeight: 700 }}>
            Cross References
          </Typography>
          <Button
            sdsType="primary"
            sdsStyle="minimal"
            disabled={readOnly}
            onClick={() => set('crossRefs', [...form.crossRefs, { type: 'publication', value: '' }])}
          >
            + Add entry
          </Button>
        </Box>
        <CrossReferencesEditor
          entries={form.crossRefs}
          onChange={(entries) => set('crossRefs', entries)}
          disabled={readOnly}
        />
      </Paper>

      <Paper variant="outlined" sx={{ p: 3, borderRadius: 2 }}>
        <AuthorTable authors={form.authors} onChange={(authors) => set('authors', authors)} disabled={readOnly} />
      </Paper>
    </Box>
  );
}
