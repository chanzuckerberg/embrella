'use client';

import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { Alert, Box, Chip, CircularProgress, ToggleButton, ToggleButtonGroup, Typography } from '@mui/material';

import { updateSession } from '../../services/depositionApi';
import { depositionKeys } from '../../queryKeys';
import { useDraftAutoSave } from '../../hooks/useDraftAutoSave';
import { useAnnotationScan } from '../../hooks/useAnnotationScan';
import { AnnotationList, annId } from '../../components/annotations/AnnotationList';
import { AnnotationMetadataForm } from '../../components/annotations/AnnotationMetadataForm';
import { annotationNeedsMetadata, mergeAnnotations, stripIncompleteLinks } from '../../components/annotations/scan';
import type { Dataset, DepositionAnnotation } from '../../types';
import type { StepProps } from '../wizardTypes';

interface SessionRef {
  key: string;
  id?: number;
  name: string;
  runs: string[];
  saved: DepositionAnnotation[];
}

function toSessionRefs(dataset: Dataset): SessionRef[] {
  return (dataset.sessions ?? []).map((s, i) => ({
    key: `ann-${s.id ?? i}`,
    id: s.id,
    name: s.msi_session_name ?? '',
    runs: Array.isArray(s.selected_copick_runs) ? (s.selected_copick_runs as string[]) : [],
    saved: s.annotations ?? [],
  }));
}

export function AnnotationsStep({ dataset, reportSave, readOnly: readOnlyProp }: StepProps) {
  const queryClient = useQueryClient();
  const readOnly = readOnlyProp || dataset.status !== 'draft';
  const sessions = useMemo(() => toSessionRefs(dataset), [dataset]);
  const [activeKey, setActiveKey] = useState(sessions[0]?.key ?? '');
  const active = sessions.find((s) => s.key === activeKey) ?? sessions[0];

  // Merged, user-editable annotation list per session (seeded from saved rows).
  const [bySession, setBySession] = useState<Record<string, DepositionAnnotation[]>>(() =>
    Object.fromEntries(sessions.map((s) => [s.key, s.saved]))
  );
  const [activeAnnId, setActiveAnnId] = useState<string | null>(null);

  const scan = useAnnotationScan(active?.name ?? '', active?.runs ?? [], !readOnly);

  useEffect(() => {
    if (!scan.data || !active) return;
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setBySession((prev) => ({
      ...prev,
      [active.key]: mergeAnnotations(scan.data.annotations, prev[active.key] ?? []),
    }));
  }, [scan.data, active]);
  const scanning = scan.isPending;

  const save = useCallback(
    async (state: Record<string, DepositionAnnotation[]>) => {
      await Promise.all(
        sessions
          .filter((s) => s.id)
          .map((s) =>
            updateSession(s.id as number, {
              annotations: (state[s.key] ?? []).filter((a) => a.is_selected).map(stripIncompleteLinks),
            })
          )
      );
      queryClient.invalidateQueries({ queryKey: depositionKeys.dataset(dataset.id) });
    },
    [dataset.id, queryClient, sessions]
  );

  const { status, lastSavedAt, saveNow } = useDraftAutoSave(bySession, save, { enabled: !readOnly });
  useEffect(() => {
    reportSave?.({ status, lastSavedAt, saveNow });
  }, [status, lastSavedAt, saveNow, reportSave]);

  const list = bySession[active?.key ?? ''] ?? [];
  const activeAnn = list.find((a) => annId(a) === activeAnnId) ?? null;

  const patchActive = (patch: Partial<DepositionAnnotation>) => {
    if (!active || !activeAnn) return;
    setBySession((prev) => ({
      ...prev,
      [active.key]: (prev[active.key] ?? []).map((a) => (annId(a) === activeAnnId ? { ...a, ...patch } : a)),
    }));
  };

  const toggle = (id: string, selected: boolean) => {
    if (!active) return;
    setBySession((prev) => ({
      ...prev,
      [active.key]: (prev[active.key] ?? []).map((a) => (annId(a) === id ? { ...a, is_selected: selected } : a)),
    }));
    setActiveAnnId(id);
  };

  const setAll = (selected: boolean) => {
    if (!active) return;
    setBySession((prev) => ({
      ...prev,
      [active.key]: (prev[active.key] ?? []).map((a) => ({ ...a, is_selected: selected })),
    }));
  };

  if (sessions.length === 0) {
    return <Alert severity="info">Add imaging sessions with copick configs on the Sources step first.</Alert>;
  }

  const needCount = list.filter(annotationNeedsMetadata).length;

  let body: ReactNode;
  if ((active?.runs.length ?? 0) === 0) {
    body = <Alert severity="info">No copick configs selected for this session on the Sources step.</Alert>;
  } else if (scanning) {
    body = (
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, py: 4, justifyContent: 'center' }}>
        <CircularProgress size={20} />
        <Typography variant="body2" color="text.secondary">
          Scanning copick configs… this can take a few minutes.
        </Typography>
      </Box>
    );
  } else {
    body = (
      <Box
        sx={{
          display: 'grid',
          gridTemplateColumns: { xs: '1fr', md: 'minmax(0, 320px) minmax(0, 1fr)' },
          gap: 3,
          alignItems: 'start',
        }}
      >
        <Box sx={{ borderRight: { md: '1px solid' }, borderColor: { md: 'divider' }, pr: { md: 2 } }}>
          {scan.isError && (
            <Alert severity="warning" sx={{ mb: 1.5 }}>
              Copick scan unavailable - showing saved annotations only.
            </Alert>
          )}
          {!scan.isError && !!scan.data && !scan.data.scanned && scan.data.annotations.length === 0 && (
            <Alert severity="info" sx={{ mb: 1.5 }}>
              No copick scan has run for these configs yet - showing saved annotations only.
            </Alert>
          )}
          {!scan.isError && !!scan.data && !scan.data.scanned && scan.data.annotations.length > 0 && (
            <Alert severity="info" sx={{ mb: 1.5 }}>
              Some selected configs haven&apos;t been scanned yet - showing available annotations.
            </Alert>
          )}
          <AnnotationList
            annotations={list}
            activeId={activeAnnId}
            onActivate={setActiveAnnId}
            onToggle={toggle}
            onSetAll={setAll}
            readOnly={readOnly}
          />
        </Box>

        <Box sx={{ position: { md: 'sticky' }, top: 0, alignSelf: 'start' }}>
          {activeAnn ? (
            <>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mb: 2 }}>
                <Typography variant="subtitle1" sx={{ fontWeight: 700, fontFamily: 'monospace' }}>
                  {activeAnn.copick_ref}
                </Typography>
                <Chip label={activeAnn.copick_kind} size="small" />
                {(active?.runs.length ?? 0) > 0 && (
                  <Chip label={`from config: ${active?.runs.join(', ')}`} size="small" />
                )}
              </Box>
              <AnnotationMetadataForm annotation={activeAnn} onChange={patchActive} readOnly={readOnly} />
            </>
          ) : (
            <Typography variant="body2" color="text.secondary" sx={{ py: 4, textAlign: 'center' }}>
              Select an annotation on the left to edit its metadata.
            </Typography>
          )}
        </Box>
      </Box>
    );
  }

  return (
    <Box>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        Choose which annotations from your copick configs to deposit, then complete the metadata for each. Only selected
        annotations are submitted.
      </Typography>

      {sessions.length > 1 && (
        <ToggleButtonGroup
          exclusive
          size="small"
          value={active?.key}
          onChange={(_, v: string | null) => {
            if (v) {
              setActiveKey(v);
              setActiveAnnId(null);
            }
          }}
          sx={{ mb: 2, flexWrap: 'wrap' }}
        >
          {sessions.map((s) => (
            <ToggleButton key={s.key} value={s.key} sx={{ textTransform: 'none' }}>
              {s.name || 'Session'}
            </ToggleButton>
          ))}
        </ToggleButtonGroup>
      )}

      {body}

      {needCount > 0 && (
        <Alert severity="warning" sx={{ mt: 2 }}>
          {needCount} selected annotation{needCount === 1 ? '' : 's'} still need a name and ontology ID.
        </Alert>
      )}
    </Box>
  );
}
