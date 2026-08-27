'use client';

import { useState } from 'react';
import { Icon, Button } from '@czi-sds/components';
import { Alert, Box, Checkbox, CircularProgress, FormControlLabel, Switch, Tab, Tabs, Typography } from '@mui/material';

import type { TiltseriesMetadata, TomogramFlavor, TomogramMetadata } from '../../types';
import { TOMOGRAM_FLAVORS } from '../../types';
import { MetadataRow, type FieldValue } from './MetadataRow';
import { YamlPreview } from './YamlPreview';
import {
  autofilledValue,
  countIssues,
  countTomogramIssues,
  groupBySection,
  isIssue,
  perFlavorTomogramFields,
  provenance,
  SECTION_SOURCE,
  SHARED_TOMOGRAM_FIELDS,
  TILTSERIES_FIELDS,
  type FieldDef,
} from './fields';
import { sessionToYaml } from './yaml';

export interface SessionMeta {
  key: string;
  id?: number;
  sessionName: string;
  aretomoRun: string;
  tiltseries: TiltseriesMetadata;
  tomograms: Record<TomogramFlavor, TomogramMetadata>;
  lastAutofillAt?: string | null;
}

type TabKey = 'tiltseries' | TomogramFlavor;
type ViewTab = 'tiltseries' | 'tomograms';

const FLAVOR_LABEL: Record<TomogramFlavor, string> = {
  denoised: 'Denoised',
  filtered: 'Filtered',
};

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
                  loading={loading}
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

const FLAVOR_FILE_SUFFIX: Record<TomogramFlavor, string> = {
  denoised: '_Vol.mrc',
  filtered: '_dctf_Vol.mrc',
};

function TomogramPanel({
  tomograms,
  readOnly,
  loading,
  columns,
  runName,
  showOnlyIssues,
  onShared,
  onFlavor,
}: {
  tomograms: Record<TomogramFlavor, TomogramMetadata>;
  readOnly: boolean;
  loading: boolean;
  columns: 1 | 2;
  runName: string;
  showOnlyIssues: boolean;
  onShared: (key: string, value: FieldValue) => void;
  onFlavor: (flavor: TomogramFlavor, key: string, value: FieldValue) => void;
}) {
  const shared = tomograms.denoised;
  const gridCols = columns === 2 ? { xs: '1fr', md: '1fr 1fr' } : '1fr';

  const sharedVisible = SHARED_TOMOGRAM_FIELDS.filter((f) => !showOnlyIssues || isIssue(f, shared as never));
  const flavorFields = (flavor: TomogramFlavor) =>
    perFlavorTomogramFields(flavor).filter((f) => !showOnlyIssues || isIssue(f, tomograms[flavor] as never));

  if (showOnlyIssues && sharedVisible.length === 0 && TOMOGRAM_FLAVORS.every((f) => flavorFields(f).length === 0)) {
    return (
      <Typography variant="body2" color="text.secondary" sx={{ py: 3, textAlign: 'center' }}>
        Nothing to fix here - everything’s filled in.
      </Typography>
    );
  }

  const gridSx = {
    display: 'grid',
    gridTemplateColumns: gridCols,
    columnGap: { xs: 2, md: 5 },
    rowGap: 1.25,
    alignItems: 'center',
  } as const;

  return (
    <Box sx={{ mt: 0.5 }}>
      {sharedVisible.length > 0 && (
        <>
          <Typography
            variant="overline"
            sx={{ fontWeight: 700, letterSpacing: 1, color: 'text.secondary', display: 'block', mb: 1 }}
          >
            RECONSTRUCTION
            <Box
              component="span"
              sx={{ ml: 1, textTransform: 'none', letterSpacing: 0, color: 'text.disabled', fontWeight: 400 }}
            >
              applies to every tomogram in this session
            </Box>
          </Typography>
          <Box sx={{ ...gridSx, mb: 3 }}>
            {sharedVisible.map((field) => (
              <MetadataRow
                key={field.key}
                field={field}
                value={(shared as Record<string, FieldValue>)[field.key]}
                provenance={provenance(field, shared as never)}
                original={autofilledValue(field, shared as never)}
                readOnly={readOnly}
                loading={loading}
                onChange={(v) => onShared(field.key, v)}
              />
            ))}
          </Box>
        </>
      )}

      {TOMOGRAM_FLAVORS.map((flavor) => {
        const fields = flavorFields(flavor);
        if (fields.length === 0) return null;
        return (
          <Box key={flavor} sx={{ mb: 2.5 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 1, mb: 1 }}>
              <Typography variant="overline" sx={{ fontWeight: 700, letterSpacing: 1, color: 'text.secondary' }}>
                {FLAVOR_LABEL[flavor].toUpperCase()}
                <Box
                  component="span"
                  sx={{ ml: 1, textTransform: 'none', letterSpacing: 0, color: 'text.disabled', fontWeight: 400 }}
                >
                  · {runName ? `${runName}${FLAVOR_FILE_SUFFIX[flavor]}` : `*${FLAVOR_FILE_SUFFIX[flavor]}`}
                </Box>
              </Typography>
              <FormControlLabel
                control={
                  <Checkbox
                    size="small"
                    checked={tomograms[flavor].is_visualization_default === true}
                    disabled={readOnly}
                    onChange={(e) => onFlavor(flavor, 'is_visualization_default', e.target.checked)}
                    sx={{ p: 0.5 }}
                  />
                }
                label={<Typography variant="caption">is_visualization_default</Typography>}
                sx={{ m: 0 }}
              />
            </Box>
            <Box sx={gridSx}>
              {fields.map((field) => (
                <MetadataRow
                  key={field.key}
                  field={field}
                  value={(tomograms[flavor] as Record<string, FieldValue>)[field.key]}
                  provenance={provenance(field, tomograms[flavor] as never)}
                  original={autofilledValue(field, tomograms[flavor] as never)}
                  readOnly={readOnly}
                  loading={loading}
                  onChange={(v) => onFlavor(flavor, field.key, v)}
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
  const [tab, setTab] = useState<ViewTab>('tiltseries');
  const [showOnlyIssues, setShowOnlyIssues] = useState(false);
  const [showYaml, setShowYaml] = useState(false);
  const hasRun = Boolean(session.aretomoRun);

  const tsIssues = countIssues(TILTSERIES_FIELDS, session.tiltseries as never);
  const tomoIssues = countTomogramIssues(session.tomograms);
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
                // Only one flavor can be the visualization default — selecting one clears the other.
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
            />
          )}
        </Box>
      </Box>
    </Box>
  );
}
