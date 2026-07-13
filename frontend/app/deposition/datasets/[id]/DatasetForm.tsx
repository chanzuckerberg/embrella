'use client';

import { useCallback, useEffect, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { Button } from '@czi-sds/components';
import AddIcon from '@mui/icons-material/Add';
import DeleteOutlineIcon from '@mui/icons-material/DeleteOutline';
import { Box, Divider, IconButton, Stack, TextField, Tooltip, Typography } from '@mui/material';

import { updateDataset } from '../../services/depositionApi';
import { depositionKeys } from '../../queryKeys';
import type { Dataset, DatasetFunding } from '../../types';
import { type AutoSaveState, useDraftAutoSave } from '../../hooks/useDraftAutoSave';
// import { SaveIndicator } from '../../components/SaveIndicator';


interface FormState {
  title: string;
  description: string;
  sample_preparation: string;
  grid_preparation: string;
  other_setup: string;
  assay_label: string;
  assay_ontology_id: string;
  dataset_publications: string;
  related_database_entries: string;
  funding: DatasetFunding[];
}

type StringKey = Exclude<keyof FormState, 'funding'>;

function toForm(d: Dataset): FormState {
  return {
    title: d.title ?? '',
    description: d.description ?? '',
    sample_preparation: d.sample_preparation ?? '',
    grid_preparation: d.grid_preparation ?? '',
    other_setup: d.other_setup ?? '',
    assay_label: d.assay_label ?? '',
    assay_ontology_id: d.assay_ontology_id ?? '',
    dataset_publications: d.dataset_publications ?? '',
    related_database_entries: d.related_database_entries ?? '',
    funding: d.funding ?? [],
  };
}

export function DatasetForm({
  dataset,
  reportSave,
}: {
  dataset: Dataset;
  reportSave?: (state: AutoSaveState) => void;
}) {
  const queryClient = useQueryClient();
  const [form, setForm] = useState<FormState>(() => toForm(dataset));
  // Only drafts are editable; once syncing/pushed the deposition is locked.
  const readOnly = dataset.status !== 'draft';

  const save = useCallback(
    async (payload: FormState) => {
      const updated = await updateDataset(dataset.id, payload);
      queryClient.setQueryData(depositionKeys.dataset(dataset.id), updated);
      queryClient.invalidateQueries({ queryKey: [...depositionKeys.all, 'submissions'] });
    },
    [dataset.id, queryClient],
  );

  const { status, lastSavedAt, saveNow } = useDraftAutoSave(form, save, { enabled: !readOnly });

  useEffect(() => {
    reportSave?.({ status, lastSavedAt, saveNow });
  }, [status, lastSavedAt, saveNow, reportSave]);

  const set = <K extends keyof FormState>(key: K, value: FormState[K]) =>
    setForm((prev) => ({ ...prev, [key]: value }));

  const setFunding = (i: number, patch: Partial<DatasetFunding>) =>
    set(
      'funding',
      form.funding.map((f, idx) => (idx === i ? { ...f, ...patch } : f)),
    );
  const addFunding = () => set('funding', [...form.funding, { funding_agency_name: '', grant_id: '' }]);
  const removeFunding = (i: number) =>
    set(
      'funding',
      form.funding.filter((_, idx) => idx !== i),
    );

  const field = (label: string, key: StringKey, opts: { multiline?: boolean; required?: boolean } = {}) => (
    <TextField
      label={label}
      value={form[key]}
      onChange={(e) => setForm((prev) => ({ ...prev, [key]: e.target.value }))}
      required={opts.required}
      multiline={opts.multiline}
      minRows={opts.multiline ? 3 : undefined}
      fullWidth
      size="small"
      disabled={readOnly}
    />
  );

  return (
    <Stack spacing={4}>
      {/* {!readOnly && !reportSave && <SaveIndicator status={status} lastSavedAt={lastSavedAt} onSaveNow={saveNow} />} */}

      <Section title="Overview">
        {field('Title', 'title', { required: true })}
        {field('Description', 'description', { multiline: true })}
      </Section>

      <Section title="Sample & grid preparation">
        {field('Sample preparation', 'sample_preparation', { multiline: true })}
        {field('Grid preparation', 'grid_preparation', { multiline: true })}
        {field('Other setup', 'other_setup', { multiline: true })}
      </Section>

      <Section title="Assay">
        <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2}>
          <Box sx={{ flex: 2 }}>{field('Assay label', 'assay_label')}</Box>
          <Box sx={{ flex: 1 }}>{field('Assay ontology ID', 'assay_ontology_id')}</Box>
        </Stack>
      </Section>

      <Section title="Publications & references">
        {field('Dataset publications', 'dataset_publications', { multiline: true })}
        {field('Related database entries', 'related_database_entries', { multiline: true })}
      </Section>

      <Section title="Funding">
        <Stack spacing={2}>
          {form.funding.length === 0 && (
            <Typography variant="body2" color="text.secondary">
              No funding sources added.
            </Typography>
          )}
          {form.funding.map((f, i) => (
            <Stack key={i} direction="row" spacing={1} alignItems="center">
              <TextField
                label="Funding agency"
                value={f.funding_agency_name}
                onChange={(e) => setFunding(i, { funding_agency_name: e.target.value })}
                size="small"
                fullWidth
                disabled={readOnly}
              />
              <TextField
                label="Grant ID"
                value={f.grant_id ?? ''}
                onChange={(e) => setFunding(i, { grant_id: e.target.value })}
                size="small"
                fullWidth
                disabled={readOnly}
              />
              {!readOnly && (
                <Tooltip title="Remove">
                  <IconButton aria-label="Remove funding" onClick={() => removeFunding(i)} size="small">
                    <DeleteOutlineIcon fontSize="small" />
                  </IconButton>
                </Tooltip>
              )}
            </Stack>
          ))}
          {!readOnly && (
            <Box>
              <Button sdsType="secondary" sdsStyle="outline" size="small" startIcon={<AddIcon />} onClick={addFunding}>
                Add funding source
              </Button>
            </Box>
          )}
        </Stack>
      </Section>
    </Stack>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <Box>
      <Typography variant="subtitle1" sx={{ fontWeight: 700, mb: 1.5 }}>
        {title}
      </Typography>
      <Divider sx={{ mb: 2 }} />
      <Stack spacing={2}>{children}</Stack>
    </Box>
  );
}
