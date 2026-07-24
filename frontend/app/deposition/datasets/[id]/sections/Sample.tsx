'use client';

import { MenuItem, Stack, TextField } from '@mui/material';

import { SectionCard } from './SectionCard';

const SAMPLE_TYPES = [
  'organism',
  'tissue',
  'organelle',
  'virus',
  'cell_line',
  'primary_cell_culture',
  'organoid',
  'in_vitro',
  'in_silico',
  'other',
];

export function Sample({
  sampleType,
  samplePreparation,
  gridPreparation,
  otherSetup,
  onChangeSampleType,
  onChangeSamplePreparation,
  onChangeGridPreparation,
  onChangeOtherSetup,
  readOnly,
  innerRef,
}: {
  sampleType: string;
  samplePreparation: string;
  gridPreparation: string;
  otherSetup: string;
  onChangeSampleType: (value: string) => void;
  onChangeSamplePreparation: (value: string) => void;
  onChangeGridPreparation: (value: string) => void;
  onChangeOtherSetup: (value: string) => void;
  readOnly: boolean;
  innerRef: (el: HTMLDivElement | null) => void;
}) {
  return (
    <SectionCard title="Sample" sectionKey="sample" innerRef={innerRef}>
      <TextField
        select
        label="Sample type"
        value={sampleType}
        onChange={(e) => onChangeSampleType(e.target.value)}
        required
        fullWidth
        size="small"
        disabled={readOnly}
        sx={{ maxWidth: { sm: 320 } }}
      >
        {SAMPLE_TYPES.map((t) => (
          <MenuItem key={t} value={t}>
            {t}
          </MenuItem>
        ))}
      </TextField>

      <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2}>
        <TextField
          label="Sample preparation"
          value={samplePreparation}
          onChange={(e) => onChangeSamplePreparation(e.target.value)}
          multiline
          minRows={4}
          fullWidth
          size="small"
          disabled={readOnly}
          sx={{ '& textarea': { resize: 'vertical' } }}
        />
        <TextField
          label="Grid preparation"
          value={gridPreparation}
          onChange={(e) => onChangeGridPreparation(e.target.value)}
          multiline
          minRows={4}
          fullWidth
          size="small"
          disabled={readOnly}
          placeholder="e.g. glow discharge + blot 3s + plunge in ethane"
          sx={{ '& textarea': { resize: 'vertical' } }}
        />
      </Stack>

      <TextField
        label="Other setup"
        value={otherSetup}
        onChange={(e) => onChangeOtherSetup(e.target.value)}
        fullWidth
        size="small"
        disabled={readOnly}
      />
    </SectionCard>
  );
}
