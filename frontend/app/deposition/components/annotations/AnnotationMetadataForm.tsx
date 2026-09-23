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
import type { AnnotationMethodType, DepositionAnnotation, DepositionMethodLink, MethodLinkType } from '../../types';
import { CollapsibleSection } from './CollapsibleSection';
import { ObjectOntologyField } from './ObjectOntologyField';
import { detailsFilled, doiCount, flagsSet, linkCount, methodFilled } from './sectionSummary';

const METHOD_TYPES: { value: AnnotationMethodType; label: string }[] = [
  { value: 'manual', label: 'Manual' },
  { value: 'automated', label: 'Automated' },
  { value: 'hybrid', label: 'Hybrid' },
  { value: 'simulated', label: 'Simulated' },
];

const LINK_TYPES: { value: MethodLinkType; label: string }[] = [
  { value: 'source_code', label: 'Source code' },
  { value: 'models_weights', label: 'Models / weights' },
  { value: 'documentation', label: 'Documentation' },
  { value: 'website', label: 'Website' },
  { value: 'other', label: 'Other' },
];

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
    <Stack spacing={1}>
      <Stack direction="row" alignItems="center" justifyContent="space-between">
        <Typography variant="body2" sx={{ fontWeight: 600 }}>
          Publications
        </Typography>
        {!disabled && (
          <Button
            size="small"
            variant="text"
            startIcon={<Icon sdsIcon="Plus" sdsSize="s" />}
            onClick={() => sync([...rows, ''])}
          >
            Add DOI
          </Button>
        )}
      </Stack>
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
              <Icon sdsIcon="TrashCan" sdsSize="s" color="red" />
            </IconButton>
          )}
        </Stack>
      ))}
    </Stack>
  );
}

function MethodLinksEditor({
  value,
  onChange,
  disabled,
}: {
  value: DepositionMethodLink[];
  onChange: (value: DepositionMethodLink[]) => void;
  disabled?: boolean;
}) {
  const update = (i: number, patch: Partial<DepositionMethodLink>) =>
    onChange(value.map((r, j) => (j === i ? { ...r, ...patch } : r)));

  return (
    <Box>
      <Stack direction="row" alignItems="center" justifyContent="space-between" sx={{ mb: 1 }}>
        <Typography variant="body2" sx={{ fontWeight: 600 }}>
          Method links
        </Typography>
        {!disabled && (
          <Button
            size="small"
            variant="text"
            startIcon={<Icon sdsIcon="Plus" sdsSize="s" />}
            onClick={() => onChange([...value, { link_type: 'source_code', link: '' }])}
          >
            Add link
          </Button>
        )}
      </Stack>
      <Stack spacing={2.5}>
        {value.map((row, i) => (
          <Stack key={i} direction="row" spacing={1} alignItems="flex-start">
            <TextField
              select
              size="small"
              label="Type"
              required
              value={row.link_type ?? ''}
              onChange={(e) => update(i, { link_type: e.target.value as MethodLinkType })}
              disabled={disabled}
              sx={{ minWidth: 160 }}
            >
              {LINK_TYPES.map((t) => (
                <MenuItem key={t.value} value={t.value}>
                  {t.label}
                </MenuItem>
              ))}
            </TextField>
            <TextField
              size="small"
              label="Link URL"
              required
              placeholder="https://…"
              value={row.link ?? ''}
              onChange={(e) => update(i, { link: e.target.value })}
              disabled={disabled}
              sx={{ flex: 2 }}
            />
            <TextField
              size="small"
              label="Custom name"
              placeholder="Optional"
              value={row.custom_name ?? ''}
              onChange={(e) => update(i, { custom_name: e.target.value })}
              disabled={disabled}
              sx={{ flex: 1 }}
            />
            {!disabled && (
              <IconButton
                aria-label="Remove link"
                size="small"
                onClick={() => onChange(value.filter((_, j) => j !== i))}
              >
                <Icon sdsIcon="TrashCan" sdsSize="s" color="red" />
              </IconButton>
            )}
          </Stack>
        ))}
      </Stack>
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

  const links = linkCount(annotation);
  const linksSuffix = links > 0 ? ` · ${links} links` : '';
  const dois = doiCount(annotation);
  const doisSuffix = dois > 0 ? ` · ${dois} DOIs` : '';
  const flags = flagsSet(annotation);
  const details = detailsFilled(annotation);
  const methods = methodFilled(annotation);

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
      <Box>
        <Typography variant="overline" sx={{ fontWeight: 700, letterSpacing: 1, color: 'text.secondary' }}>
          OBJECT{' '}
          <Box component="span" sx={{ letterSpacing: 0, textTransform: 'none', color: 'text.disabled' }}>
            Name and ontology ID are required
          </Box>
        </Typography>
        <ObjectOntologyField
          name={annotation.object_name ?? ''}
          id={annotation.object_id ?? ''}
          onChange={onChange}
          disabled={readOnly}
          sx={{ mt: 2 }}
        />
      </Box>

      <CollapsibleSection
        title="Method & links"
        summary={`${methods} of 2 filled${linksSuffix}`}
        defaultOpen={methods > 0 || links > 0}
      >
        <Box
          sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', sm: 'repeat(3, 1fr)' }, columnGap: 2, rowGap: 2.5 }}
        >
          {text('annotation_method', 'Annotation method')}
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
          {text('annotation_software', 'Annotation software')}
        </Box>
        <Box sx={{ mt: 2.5 }}>
          <MethodLinksEditor
            value={annotation.method_links ?? []}
            onChange={(v) => onChange({ method_links: v })}
            disabled={readOnly}
          />
        </Box>
      </CollapsibleSection>

      <CollapsibleSection
        title="Details"
        summary={`${details + flags} of 4 filled${doisSuffix}`}
        defaultOpen={details > 0 || flags > 0 || dois > 0}
      >
        <Stack spacing={3}>
          <Box
            sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', sm: '3fr 7fr' }, gap: 2, alignItems: 'stretch' }}
          >
            <TextField
              label="Object state"
              value={annotation.object_state ?? ''}
              onChange={(e) => onChange({ object_state: e.target.value })}
              size="small"
              fullWidth
              disabled={readOnly}
              sx={{ '& .MuiOutlinedInput-root': { height: '100%', alignItems: 'flex-start' } }}
            />
            {text('object_description', 'Object description', true)}
          </Box>

          <AnnotationPublications
            value={annotation.annotation_publication ?? ''}
            onChange={(v) => onChange({ annotation_publication: v })}
            disabled={readOnly}
          />

          <Box>
            <Typography variant="body2" sx={{ fontWeight: 600, mb: 1 }}>
              Flags
            </Typography>
            <Stack direction={{ xs: 'column', sm: 'row' }} spacing={{ xs: 1.5, sm: 3 }}>
              <FormControlLabel
                sx={{ m: 0 }}
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
                sx={{ m: 0 }}
                control={
                  <Checkbox
                    checked={!!annotation.is_visualization_default}
                    onChange={(e) => onChange({ is_visualization_default: e.target.checked })}
                    disabled={readOnly}
                  />
                }
                label="Default in viewer"
              />
            </Stack>
          </Box>
        </Stack>
      </CollapsibleSection>
    </Box>
  );
}
