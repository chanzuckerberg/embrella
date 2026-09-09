'use client';

import { useState } from 'react';
import { Icon } from '@czi-sds/components';
import {
  Box,
  Button,
  Checkbox,
  FormControlLabel,
  IconButton,
  MenuItem,
  Stack,
  TextField,
  Typography,
} from '@mui/material';

import { IdentifierField } from '../IdentifierField';
import { OntologyIdInput } from '../../datasets/[id]/sections/OntologyIdInput';
import type { AnnotationMethodType, DepositionAnnotation } from '../../types';

const OBJECT_ONTOLOGIES = [
  {
    type: 'GO',
    ontology: 'go',
    pattern: '^GO:[0-9]{7}$',
    prefix: 'GO',
    lookup: 'https://www.ebi.ac.uk/ols4/ontologies/go',
  },
  {
    type: 'UBERON',
    ontology: 'uberon',
    pattern: '^UBERON:[0-9]{7}$',
    prefix: 'UBERON',
    lookup: 'https://www.ebi.ac.uk/ols4/ontologies/uberon',
  },
  {
    type: 'CHEBI',
    ontology: 'chebi',
    pattern: '^CHEBI:[0-9]+$',
    prefix: 'CHEBI',
    lookup: 'https://www.ebi.ac.uk/ols4/ontologies/chebi',
  },
  {
    type: 'UniProtKB',
    ontology: '',
    pattern: '^UniProtKB:(?:[OPQ][0-9][A-Z0-9]{3}[0-9]|[A-NR-Z][0-9](?:[A-Z][A-Z0-9]{2}[0-9]){1,2})$',
    prefix: 'UniProtKB',
    lookup: 'https://www.uniprot.org',
    manualOnly: true,
  },
  {
    type: 'CDPO',
    ontology: '',
    pattern: '^CDPO:[0-9]{7}$',
    prefix: 'CDPO',
    lookup: 'https://cryoetdataportal.czscience.com',
    manualOnly: true,
  },
] as const;

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

function AnnotationPublications({
  value,
  onChange,
  disabled,
}: {
  value: string;
  onChange: (value: string) => void;
  disabled?: boolean;
}) {
  const [rows, setRows] = useState<string[]>(() =>
    value
      .split(',')
      .map((s) => s.trim())
      .filter(Boolean)
  );
  const sync = (next: string[]) => {
    setRows(next);
    onChange(
      next
        .map((s) => s.trim())
        .filter(Boolean)
        .join(', ')
    );
  };

  return (
    <Box>
      <SectionLabel>Publications</SectionLabel>
      <Stack spacing={1}>
        {rows.map((doi, i) => (
          <Stack key={i} direction="row" spacing={1} alignItems="flex-start">
            <IdentifierField
              kind="doi"
              size="small"
              fullWidth
              placeholder="10.1021/…"
              value={doi}
              disabled={disabled}
              onChange={(v) => sync(rows.map((d, j) => (j === i ? v : d)))}
            />
            {!disabled && (
              <IconButton aria-label="Remove DOI" size="small" onClick={() => sync(rows.filter((_, j) => j !== i))}>
                <Icon sdsIcon="TrashCan" sdsSize="s" color="gray" />
              </IconButton>
            )}
          </Stack>
        ))}
        {!disabled && (
          <Button
            size="small"
            variant="text"
            startIcon={<Icon sdsIcon="Plus" sdsSize="s" />}
            onClick={() => sync([...rows, ''])}
            sx={{ alignSelf: 'flex-start' }}
          >
            Add DOI
          </Button>
        )}
      </Stack>
    </Box>
  );
}

function ObjectOntologyField({
  name,
  id,
  onChange,
  disabled,
}: {
  name: string;
  id: string;
  onChange: (patch: Partial<DepositionAnnotation>) => void;
  disabled?: boolean;
}) {
  const detected = OBJECT_ONTOLOGIES.find((o) => id.startsWith(`${o.prefix}:`)) ?? OBJECT_ONTOLOGIES[0];
  const [type, setType] = useState<string>(detected.type);
  const cfg = OBJECT_ONTOLOGIES.find((o) => o.type === type) ?? OBJECT_ONTOLOGIES[0];

  return (
    <Box>
      <TextField
        select
        size="small"
        label="Ontology"
        value={type}
        onChange={(e) => setType(e.target.value)}
        disabled={disabled}
        sx={{ minWidth: 160, mb: 2 }}
      >
        {OBJECT_ONTOLOGIES.map((o) => (
          <MenuItem key={o.type} value={o.type}>
            {o.type}
          </MenuItem>
        ))}
      </TextField>
      <OntologyIdInput
        label="Object"
        ontology={cfg.ontology}
        pattern={cfg.pattern}
        prefix={cfg.prefix}
        lookup={cfg.lookup}
        manualOnly={'manualOnly' in cfg && cfg.manualOnly}
        name={name}
        id={id}
        onChange={(p) => {
          const patch: Partial<DepositionAnnotation> = {};
          if (p.name !== undefined) patch.object_name = p.name;
          if (p.id !== undefined) patch.object_id = p.id;
          onChange(patch);
        }}
        disabled={disabled}
      />
    </Box>
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

  const grid = { display: 'grid', gridTemplateColumns: { xs: '1fr', sm: '1fr 1fr' }, columnGap: 2, rowGap: 2.5 };

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
      <Box>
        <SectionLabel>Object</SectionLabel>
        <ObjectOntologyField
          key={`${annotation.copick_kind}:${annotation.copick_ref}`}
          name={annotation.object_name ?? ''}
          id={annotation.object_id ?? ''}
          onChange={onChange}
          disabled={readOnly}
        />
        <Box sx={{ ...grid, mt: 2 }}>
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
            <MenuItem value=""></MenuItem>
            {METHOD_TYPES.map((m) => (
              <MenuItem key={m.value} value={m.value}>
                {m.label}
              </MenuItem>
            ))}
          </TextField>
        </Box>
      </Box>

      <AnnotationPublications
        key={`${annotation.copick_kind}:${annotation.copick_ref}`}
        value={annotation.annotation_publication ?? ''}
        onChange={(v) => onChange({ annotation_publication: v })}
        disabled={readOnly}
      />

      <Box sx={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap', gap: 2 }}>
        <SectionLabel>Flags</SectionLabel>
        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 3 }}>
          <FormControlLabel
            control={
              <Checkbox
                checked={!!annotation.ground_truth_status}
                onChange={(e) => onChange({ ground_truth_status: e.target.checked })}
                disabled={readOnly}
              />
            }
            label="Ground truth"
          />
          <FormControlLabel
            control={
              <Checkbox
                checked={!!annotation.is_visualization_default}
                onChange={(e) => onChange({ is_visualization_default: e.target.checked })}
                disabled={readOnly}
              />
            }
            label="is_visualization_default"
          />
        </Box>
      </Box>
    </Box>
  );
}
