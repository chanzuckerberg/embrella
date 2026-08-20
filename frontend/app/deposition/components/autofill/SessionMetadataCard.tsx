'use client';

import { useState } from 'react';
import DescriptionOutlinedIcon from '@mui/icons-material/DescriptionOutlined';
import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  FormControlLabel,
  Switch,
  ToggleButton,
  ToggleButtonGroup,
  Typography,
} from '@mui/material';

import type { TiltseriesMetadata, TomogramMetadata } from '../../types';
import { MetadataRow, type FieldValue } from './MetadataRow';
import { YamlPreview } from './YamlPreview';
import {
  autofilledValue,
  coerceValue,
  countIssues,
  groupBySection,
  isIssue,
  provenance,
  SECTION_SOURCE,
  TILTSERIES_FIELDS,
  TOMOGRAM_FIELDS,
  type FieldDef,
} from './fields';
import { parseSessionYaml, sessionToYaml } from './yaml';

export interface SessionMeta {
  key: string;
  id?: number;
  sessionName: string;
  aretomoRun: string;
  tiltseries: TiltseriesMetadata;
  tomogram: TomogramMetadata;
  lastAutofillAt?: string | null;
}

type Tab = 'tiltseries' | 'tomogram';

function MetadataTable({
  fields,
  meta,
  readOnly,
  showOnlyIssues,
  columns,
  onChange,
}: {
  fields: FieldDef[];
  meta: TiltseriesMetadata | TomogramMetadata;
  readOnly: boolean;
  showOnlyIssues: boolean;
  columns: 1 | 2;
  onChange: (key: string, value: FieldValue) => void;
}) {
  const visible = showOnlyIssues ? fields.filter((f) => isIssue(f, meta as never)) : fields;
  if (visible.length === 0) {
    return (
      <Typography variant="body2" color="text.secondary" sx={{ py: 3, textAlign: 'center' }}>
        Nothing to fix here — everything’s filled in.
      </Typography>
    );
  }
  const trio = 'max-content minmax(0, 1fr) max-content';
  const gridCols = columns === 2 ? { xs: trio, md: `${trio} ${trio}` } : trio;
  return (
    <Box sx={{ mt: 1 }}>
      {groupBySection(visible).map((group) => (
        <Box key={group.section} sx={{ mb: 2.5 }}>
          <Typography variant="overline" sx={{ fontWeight: 700, letterSpacing: 1, display: 'block', mb: 1 }}>
            <Box component="span" sx={{ color: 'text.primary' }}>
              {group.section.toUpperCase()}
            </Box>
            {SECTION_SOURCE[group.section] && (
              <Box component="span" sx={{ color: 'text.disabled' }}>
                {` · ${SECTION_SOURCE[group.section].toUpperCase()}`}
              </Box>
            )}
          </Typography>
          <Box
            sx={{ display: 'grid', gridTemplateColumns: gridCols, alignItems: 'center', columnGap: 3, rowGap: 1.75 }}
          >
            {group.fields.map((field) => (
              <MetadataRow
                key={field.key}
                field={field}
                value={(meta as Record<string, FieldValue>)[field.key]}
                provenance={provenance(field, meta as never)}
                original={autofilledValue(field, meta as never)}
                readOnly={readOnly}
                onChange={(v) => onChange(field.key, v)}
              />
            ))}
          </Box>
        </Box>
      ))}
    </Box>
  );
}

function TabLabel({ label, issues }: { label: string; issues: number }) {
  return (
    <Box sx={{ display: 'inline-flex', alignItems: 'center', gap: 0.75 }}>
      {label}
      {issues > 0 && (
        <Chip
          label={`${issues} to fix`}
          size="small"
          color="error"
          variant="outlined"
          sx={{ height: 20, '& .MuiChip-label': { px: 0.75, fontSize: '0.7rem', fontWeight: 700 } }}
        />
      )}
    </Box>
  );
}

export function SessionMetadataCard({
  session,
  readOnly,
  autoFilling,
  autoFillError,
  onAutoFill,
  onFieldChange,
}: {
  session: SessionMeta;
  readOnly: boolean;
  autoFilling: boolean;
  autoFillError?: string | null;
  onAutoFill: () => void;
  onFieldChange: (tab: Tab, key: string, value: FieldValue) => void;
}) {
  const [tab, setTab] = useState<Tab>('tiltseries');
  const [showOnlyIssues, setShowOnlyIssues] = useState(false);
  const [showYaml, setShowYaml] = useState(false);
  const hasRun = Boolean(session.aretomoRun);

  const tsIssues = countIssues(TILTSERIES_FIELDS, session.tiltseries as never);
  const tomoIssues = countIssues(TOMOGRAM_FIELDS, session.tomogram as never);

  const fields = tab === 'tiltseries' ? TILTSERIES_FIELDS : TOMOGRAM_FIELDS;
  const meta = tab === 'tiltseries' ? session.tiltseries : session.tomogram;
  const sessionLabel = session.sessionName || 'Session';
  const yamlTitle = session.aretomoRun ? `${sessionLabel} · ${session.aretomoRun}` : sessionLabel;

  // Raw-YAML editor writes recognized keys back to the modeled fields (DB source of truth).
  const applyYaml = (text: string) => {
    const parsed = parseSessionYaml(text);
    for (const f of TILTSERIES_FIELDS) {
      if (f.key in parsed.tiltseries) onFieldChange('tiltseries', f.key, coerceValue(f, parsed.tiltseries[f.key]));
    }
    for (const f of TOMOGRAM_FIELDS) {
      if (f.key in parsed.tomograms) onFieldChange('tomogram', f.key, coerceValue(f, parsed.tomograms[f.key]));
    }
  };

  return (
    <Box sx={{ border: '1px solid', borderColor: 'divider', borderRadius: 2, overflow: 'hidden' }}>
      <Box
        sx={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: 2,
          p: 2,
          bgcolor: 'grey.50',
          borderBottom: '1px solid',
          borderColor: 'divider',
        }}
      >
        <Box sx={{ minWidth: 0 }}>
          <Typography variant="subtitle1" sx={{ fontWeight: 700 }} noWrap>
            {session.sessionName || 'Unnamed session'}
            {session.aretomoRun ? ` · ${session.aretomoRun}` : ''}
          </Typography>
          <Typography variant="caption" color="text.secondary">
            {session.lastAutofillAt
              ? `Auto-filled ${new Date(session.lastAutofillAt).toLocaleString()}`
              : 'Not auto-filled yet'}
          </Typography>
        </Box>
        {!readOnly && (
          <Button
            variant="outlined"
            size="small"
            startIcon={autoFilling && <CircularProgress size={16} />}
            disabled={autoFilling || !hasRun}
            onClick={onAutoFill}
            sx={{ flexShrink: 0, textTransform: 'none', fontWeight: 600 }}
          >
            {session.lastAutofillAt ? 'Re-run auto-fill' : 'Auto-fill'}
          </Button>
        )}
      </Box>

      <Box sx={{ px: 2, pb: 2 }}>
        {!hasRun && (
          <Alert severity="info" sx={{ mt: 2 }}>
            Pick an AreTomo run for this session on the Sources step to enable auto-fill.
          </Alert>
        )}
        {autoFillError && (
          <Alert severity="error" sx={{ mt: 2 }}>
            {autoFillError}
          </Alert>
        )}

        <Box
          sx={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            flexWrap: 'wrap',
            gap: 1.5,
            mt: 2,
          }}
        >
          <ToggleButtonGroup exclusive size="small" value={tab} onChange={(_, v: Tab | null) => v && setTab(v)}>
            <ToggleButton value="tiltseries" sx={{ textTransform: 'none' }}>
              <TabLabel label="Tilt series" issues={tsIssues} />
            </ToggleButton>
            <ToggleButton value="tomogram" sx={{ textTransform: 'none' }}>
              <TabLabel label="Tomogram" issues={tomoIssues} />
            </ToggleButton>
          </ToggleButtonGroup>

          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <FormControlLabel
              control={
                <Switch size="small" checked={showOnlyIssues} onChange={(e) => setShowOnlyIssues(e.target.checked)} />
              }
              label={<Typography variant="body2">Show only issues</Typography>}
            />
            <Button
              size="small"
              onClick={() => setShowYaml((o) => !o)}
              startIcon={<DescriptionOutlinedIcon />}
              sx={{ textTransform: 'none', fontWeight: 600, color: showYaml ? 'primary.main' : 'text.secondary' }}
            >
              {showYaml ? 'Hide YAML' : 'View YAML'}
            </Button>
          </Box>
        </Box>

        <Box
          sx={{
            display: 'grid',
            gridTemplateColumns: showYaml ? { xs: '1fr', md: 'minmax(0, 1fr) minmax(340px, 440px)' } : '1fr',
            gap: 2,
            mt: 1.5,
            alignItems: 'start',
          }}
        >
          <MetadataTable
            fields={fields}
            meta={meta}
            readOnly={readOnly}
            showOnlyIssues={showOnlyIssues}
            columns={showYaml ? 1 : 2}
            onChange={(key, v) => onFieldChange(tab, key, v)}
          />
          {showYaml && (
            <YamlPreview
              yaml={sessionToYaml(session.tiltseries, session.tomogram)}
              title={yamlTitle}
              readOnly={readOnly}
              onClose={() => setShowYaml(false)}
              onApply={applyYaml}
            />
          )}
        </Box>
      </Box>
    </Box>
  );
}
