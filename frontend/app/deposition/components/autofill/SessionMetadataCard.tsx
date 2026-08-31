'use client';

import { useState } from 'react';
import { Icon, Button } from '@czi-sds/components';
import { Alert, Box, CircularProgress, FormControlLabel, Switch, Tab, Tabs, Typography } from '@mui/material';

import type { TiltseriesMetadata, TomogramFlavor, TomogramMetadata } from '../../types';
import { TOMOGRAM_FLAVORS } from '../../types';
import type { FieldValue } from './MetadataRow';
import { FieldGrid, NothingToFix } from './FieldGrid';
import { TomogramPanel } from './TomogramPanel';
import { YamlPreview } from './YamlPreview';
import {
  countIssues,
  countTomogramIssues,
  groupBySection,
  isIssue,
  SECTION_SOURCE,
  TILTSERIES_FIELDS,
  type FieldDef,
} from './fields';
import { sessionToYaml, yamlToSession } from './yaml';

export interface SessionMeta {
  key: string;
  id?: number;
  sessionName: string;
  aretomoRun: string;
  tiltseries: TiltseriesMetadata;
  tomograms: Record<TomogramFlavor, TomogramMetadata>;
  lastAutofillAt?: string | null;
}

export type TabKey = 'tiltseries' | TomogramFlavor;
type ViewTab = 'tiltseries' | 'tomograms';

function tabLabel(name: string, issues: number) {
  return (
    <Box component="span">
      {name}
      {issues > 0 && (
        <Box component="span" sx={{ color: 'error.main' }}>
          {` · ${issues} to fix`}
        </Box>
      )}
    </Box>
  );
}

function MetadataTable({
  fields,
  meta,
  readOnly,
  showOnlyIssues,
  columns,
  loading,
  onChange,
}: {
  fields: FieldDef[];
  meta: TiltseriesMetadata | TomogramMetadata;
  readOnly: boolean;
  showOnlyIssues: boolean;
  columns: 1 | 2;
  loading: boolean;
  onChange: (key: string, value: FieldValue) => void;
}) {
  const visible = showOnlyIssues ? fields.filter((f) => isIssue(f, meta as never)) : fields;
  if (visible.length === 0) {
    return <NothingToFix />;
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
            <FieldGrid
              fields={group.fields}
              meta={meta as Record<string, FieldValue>}
              columns={cols}
              readOnly={readOnly}
              loading={loading}
              onChange={onChange}
            />
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
  const [tab, setTab] = useState<ViewTab>('tiltseries');
  const [showOnlyIssues, setShowOnlyIssues] = useState(false);
  const [showYaml, setShowYaml] = useState(false);
  const hasRun = Boolean(session.aretomoRun);

  const tsIssues = countIssues(TILTSERIES_FIELDS, session.tiltseries as never);
  const tomoIssues = countTomogramIssues(session.tomograms);
  const sessionLabel = session.sessionName || 'Session';
  const yamlTitle = session.aretomoRun ? `${sessionLabel} · ${session.aretomoRun}` : sessionLabel;

  const applyYaml = (text: string) => {
    const { tiltseries, shared, perFlavor } = yamlToSession(text);
    for (const [k, v] of Object.entries(tiltseries)) onFieldChange('tiltseries', k, v);
    for (const [k, v] of Object.entries(shared)) {
      onFieldChange('denoised', k, v);
      onFieldChange('filtered', k, v);
    }
    for (const flavor of TOMOGRAM_FLAVORS) {
      for (const [k, v] of Object.entries(perFlavor[flavor])) onFieldChange(flavor, k, v);
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
            sdsType="primary"
            sdsStyle="outline"
            size="small"
            startIcon={autoFilling ? <CircularProgress size={14} /> : undefined}
            disabled={autoFilling || !hasRun}
            onClick={onAutoFill}
            sx={{ flexShrink: 0 }}
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
            onChange={(_, v: ViewTab) => setTab(v)}
            sx={{
              minHeight: 36,
              '& .MuiTab-root': { minHeight: 36, py: 0.5, textTransform: 'none', fontWeight: 600 },
            }}
          >
            <Tab value="tiltseries" label={tabLabel('Tilt series', tsIssues)} />
            <Tab value="tomograms" label={tabLabel('Tomograms', tomoIssues)} />
          </Tabs>

          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, pb: 0.25 }}>
            <FormControlLabel
              control={
                <Switch size="small" checked={showOnlyIssues} onChange={(e) => setShowOnlyIssues(e.target.checked)} />
              }
              label={<Typography variant="body2">Show only issues</Typography>}
              sx={{ mr: 0.5 }}
            />
            <Button sdsType="primary" sdsStyle="minimal" size="small" onClick={() => setShowYaml((o) => !o)}>
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
          {tab === 'tiltseries' ? (
            <MetadataTable
              fields={TILTSERIES_FIELDS}
              meta={session.tiltseries}
              readOnly={readOnly}
              showOnlyIssues={showOnlyIssues}
              columns={showYaml ? 1 : 2}
              loading={autoFilling}
              onChange={(key, v) => onFieldChange('tiltseries', key, v)}
            />
          ) : (
            <TomogramPanel
              tomograms={session.tomograms}
              readOnly={readOnly}
              loading={autoFilling}
              columns={showYaml ? 1 : 2}
              runName={session.aretomoRun}
              showOnlyIssues={showOnlyIssues}
              onShared={(key, v) => {
                onFieldChange('denoised', key, v);
                onFieldChange('filtered', key, v);
              }}
              onFlavor={(flavor, key, v) => {
                onFieldChange(flavor, key, v);
                if (key === 'is_visualization_default' && v === true) {
                  const other = flavor === 'denoised' ? 'filtered' : 'denoised';
                  onFieldChange(other, 'is_visualization_default', false);
                }
              }}
            />
          )}
          {showYaml && (
            <YamlPreview
              yaml={sessionToYaml(session.tiltseries, session.tomograms)}
              title={yamlTitle}
              onClose={() => setShowYaml(false)}
              onChange={readOnly ? undefined : applyYaml}
            />
          )}
        </Box>
      </Box>
    </Box>
  );
}
