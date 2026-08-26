'use client';

import { useState } from 'react';
import { Icon } from '@czi-sds/components';
import { Alert, Box, Button, CircularProgress, FormControlLabel, Switch, Tab, Tabs, Typography } from '@mui/material';

import type { TiltseriesMetadata, TomogramMetadata } from '../../types';
import { MetadataRow, type FieldValue } from './MetadataRow';
import { YamlPreview } from './YamlPreview';
import {
  autofilledValue,
  countIssues,
  groupBySection,
  isIssue,
  provenance,
  SECTION_SOURCE,
  TILTSERIES_FIELDS,
  TOMOGRAM_FIELDS,
  type FieldDef,
} from './fields';
import { sessionToYaml } from './yaml';

export interface SessionMeta {
  key: string;
  id?: number;
  sessionName: string;
  aretomoRun: string;
  tiltseries: TiltseriesMetadata;
  tomogram: TomogramMetadata;
  lastAutofillAt?: string | null;
}

type TabKey = 'tiltseries' | 'tomogram';

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
        Nothing to fix here - everything’s filled in.
      </Typography>
    );
  }

  return (
    <Box sx={{ mt: 0.5 }}>
      {groupBySection(visible).map((group) => {
        const isPaths = group.section === 'Paths';
        const cols = isPaths || columns === 1 ? 1 : 2;
        return (
          <Box key={group.section} sx={{ mb: 2.5 }}>
            <Typography
              variant="overline"
              sx={{ fontWeight: 700, letterSpacing: 1, display: 'block', mb: 1, lineHeight: 1.4 }}
            >
              <Box component="span" sx={{ color: 'text.secondary' }}>
                {group.section.toUpperCase()}
              </Box>
              {SECTION_SOURCE[group.section] && (
                <Box component="span" sx={{ color: 'text.disabled' }}>
                  {` · ${SECTION_SOURCE[group.section].toUpperCase()}`}
                </Box>
              )}
            </Typography>
            <Box
              sx={{
                display: 'grid',
                gridTemplateColumns: cols === 2 ? { xs: '1fr', md: '1fr 1fr' } : '1fr',
                columnGap: { xs: 2, md: 5 },
                rowGap: 1.25,
                alignItems: 'center',
              }}
            >
              {group.fields.map((field) => (
                <MetadataRow
                  key={field.key}
                  field={field}
                  value={(meta as Record<string, FieldValue>)[field.key]}
                  provenance={provenance(field, meta as never)}
                  original={autofilledValue(field, meta as never)}
                  readOnly={readOnly}
                  wide={isPaths}
                  onChange={(v) => onChange(field.key, v)}
                />
              ))}
            </Box>
          </Box>
        );
      })}
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
  onFieldChange: (tab: TabKey, key: string, value: FieldValue) => void;
}) {
  const [tab, setTab] = useState<TabKey>('tiltseries');
  const [showOnlyIssues, setShowOnlyIssues] = useState(false);
  const [showYaml, setShowYaml] = useState(false);
  const hasRun = Boolean(session.aretomoRun);

  const tsIssues = countIssues(TILTSERIES_FIELDS, session.tiltseries as never);
  const tomoIssues = countIssues(TOMOGRAM_FIELDS, session.tomogram as never);

  const fields = tab === 'tiltseries' ? TILTSERIES_FIELDS : TOMOGRAM_FIELDS;
  const meta = tab === 'tiltseries' ? session.tiltseries : session.tomogram;
  const sessionLabel = session.sessionName || 'Session';
  const yamlTitle = session.aretomoRun ? `${sessionLabel} · ${session.aretomoRun}` : sessionLabel;

  return (
    <Box sx={{ border: '1px solid', borderColor: 'divider', borderRadius: 2, overflow: 'hidden' }}>
      <Box
        sx={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: 2,
          px: 2,
          pt: 1.5,
          pb: 1,
        }}
      >
        <Box sx={{ minWidth: 0 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.75, minWidth: 0 }}>
            <Typography variant="subtitle1" sx={{ fontWeight: 700 }} noWrap>
              {session.sessionName || 'Unnamed session'}
              {session.aretomoRun ? ` · ${session.aretomoRun}` : ''}
            </Typography>
            {tsIssues + tomoIssues === 0 && (
              <Box component="span" sx={{ display: 'inline-flex', flexShrink: 0 }} title="Complete">
                <Icon sdsIcon="CheckCircle" sdsSize="s" color="green" />
              </Box>
            )}
          </Box>
          <Typography variant="caption" color="text.secondary">
            {session.lastAutofillAt
              ? `Auto-filled ${new Date(session.lastAutofillAt).toLocaleString()}`
              : 'Not auto-filled yet'}
          </Typography>
        </Box>
        {!readOnly && (
          <Button
            variant="text"
            size="small"
            startIcon={autoFilling ? <CircularProgress size={14} /> : undefined}
            disabled={autoFilling || !hasRun}
            onClick={onAutoFill}
            sx={{ flexShrink: 0, textTransform: 'none', fontWeight: 600, px: 1 }}
          >
            {session.lastAutofillAt ? 'Re-run auto-fill' : 'Auto-fill'}
          </Button>
        )}
      </Box>

      <Box sx={{ px: 2, pb: 2 }}>
        {!hasRun && (
          <Alert severity="info" sx={{ mb: 1.5 }}>
            Pick an AreTomo run for this session on the Sources step to enable auto-fill.
          </Alert>
        )}
        {autoFillError && (
          <Alert severity="error" sx={{ mb: 1.5 }}>
            {autoFillError}
          </Alert>
        )}

        <Box
          sx={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            flexWrap: 'wrap',
            gap: 1,
            borderBottom: '1px solid',
            borderColor: 'divider',
            mb: 1.5,
          }}
        >
          <Tabs
            value={tab}
            onChange={(_, v: TabKey) => setTab(v)}
            sx={{
              minHeight: 36,
              '& .MuiTab-root': { minHeight: 36, py: 0.5, textTransform: 'none', fontWeight: 600 },
            }}
          >
            <Tab value="tiltseries" label={tsIssues > 0 ? `Tilt series · ${tsIssues} to fix` : 'Tilt series'} />
            <Tab value="tomogram" label={tomoIssues > 0 ? `Tomogram · ${tomoIssues} to fix` : 'Tomogram'} />
          </Tabs>

          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, pb: 0.25 }}>
            <FormControlLabel
              control={
                <Switch size="small" checked={showOnlyIssues} onChange={(e) => setShowOnlyIssues(e.target.checked)} />
              }
              label={<Typography variant="body2">Show only issues</Typography>}
              sx={{ mr: 0.5 }}
            />
            <Button size="small" onClick={() => setShowYaml((o) => !o)} sx={{ textTransform: 'none', fontWeight: 600 }}>
              {showYaml ? 'Hide YAML' : 'View YAML'}
            </Button>
          </Box>
        </Box>

        <Box
          sx={{
            display: 'grid',
            gridTemplateColumns: showYaml ? { xs: '1fr', md: 'minmax(0, 1fr) minmax(340px, 440px)' } : '1fr',
            gap: 2,
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
              onClose={() => setShowYaml(false)}
            />
          )}
        </Box>
      </Box>
    </Box>
  );
}
