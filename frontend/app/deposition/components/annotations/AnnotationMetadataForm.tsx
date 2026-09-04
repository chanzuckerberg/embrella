'use client';

import { Box, FormControlLabel, MenuItem, Switch, TextField, Typography } from '@mui/material';

import type { AnnotationMethodType, DepositionAnnotation } from '../../types';

const METHOD_TYPES: { value: AnnotationMethodType; label: string }[] = [
  { value: 'manual', label: 'Manual' },
  { value: 'automated', label: 'Automated' },
  { value: 'hybrid', label: 'Hybrid' },
  { value: 'simulated', label: 'Simulated' },
];

function SectionLabel({ children }: { children: string }) {
  return (
    <Typography
      variant="overline"
      sx={{ fontWeight: 700, letterSpacing: 1, color: 'text.secondary', display: 'block', mb: 1 }}
    >
      {children}
    </Typography>
  );
}

export function AnnotationMetadataForm({
  annotation,
  onChange,
  readOnly = false,
}: {
  annotation: DepositionAnnotation;
  onChange: (patch: Partial<DepositionAnnotation>) => void;
  readOnly?: boolean;
}) {
  const text = (key: keyof DepositionAnnotation, label: string, multiline = false) => (
    <TextField
      label={label}
      value={(annotation[key] as string) ?? ''}
      onChange={(e) => onChange({ [key]: e.target.value } as Partial<DepositionAnnotation>)}
      size="small"
      fullWidth
      disabled={readOnly}
      multiline={multiline}
      minRows={multiline ? 2 : undefined}
    />
  );

  const grid = { display: 'grid', gridTemplateColumns: { xs: '1fr', sm: '1fr 1fr' }, gap: 2 };

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
      <Box>
        <SectionLabel>Object</SectionLabel>
        <Box sx={grid}>
          {text('object_name', 'Object name')}
          {text('object_id', 'Object ID (ontology)')}
          {text('object_state', 'Object state')}
          <TextField
            label="Object count"
            type="number"
            value={annotation.object_count ?? ''}
            onChange={(e) => onChange({ object_count: e.target.value === '' ? null : Number(e.target.value) })}
            size="small"
            fullWidth
            disabled={readOnly}
          />
        </Box>
        <Box sx={{ mt: 2 }}>{text('object_description', 'Object description', true)}</Box>
      </Box>

      <Box>
        <SectionLabel>Method</SectionLabel>
        <Box sx={grid}>
          {text('annotation_method', 'Annotation method')}
          {text('annotation_software', 'Annotation software')}
          <TextField
            select
            label="Method type"
            value={annotation.method_type ?? ''}
            onChange={(e) => onChange({ method_type: e.target.value as AnnotationMethodType })}
            size="small"
            fullWidth
            disabled={readOnly}
          >
            <MenuItem value="">
              <em>Not set</em>
            </MenuItem>
            {METHOD_TYPES.map((m) => (
              <MenuItem key={m.value} value={m.value}>
                {m.label}
              </MenuItem>
            ))}
          </TextField>
          {text('annotation_publication', 'Annotation publication')}
        </Box>
      </Box>

      <Box>
        <SectionLabel>Flags</SectionLabel>
        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 3 }}>
          <FormControlLabel
            control={
              <Switch
                checked={!!annotation.ground_truth_status}
                onChange={(e) => onChange({ ground_truth_status: e.target.checked })}
                disabled={readOnly}
              />
            }
            label="Ground truth"
          />
          <FormControlLabel
            control={
              <Switch
                checked={!!annotation.is_visualization_default}
                onChange={(e) => onChange({ is_visualization_default: e.target.checked })}
                disabled={readOnly}
              />
            }
            label="Default in viewer"
          />
        </Box>
      </Box>
    </Box>
  );
}
