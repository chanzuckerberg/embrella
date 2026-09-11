'use client';

import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { Alert, Box, Button, Chip, CircularProgress, ToggleButton, ToggleButtonGroup, Typography } from '@mui/material';

import { rescanCopick, updateSession } from '../../services/depositionApi';
import { depositionKeys } from '../../queryKeys';
import { useDraftAutoSave } from '../../hooks/useDraftAutoSave';
import { useAnnotationScan } from '../../hooks/useAnnotationScan';
import { AnnotationList, annId } from '../../components/annotations/AnnotationList';
import { AnnotationMetadataForm } from '../../components/annotations/AnnotationMetadataForm';
import {
  annotationNeedsMetadata,
  mergeAnnotations,
  mergeServerIds,
  staleAnnotationIds,
  stripIncompleteLinks,
} from '../../components/annotations/scan';
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
  const active = useMemo(() => sessions.find((s) => s.key === activeKey) ?? sessions[0], [sessions, activeKey]);

  // Merged, user-editable annotation list per session (seeded from saved rows).
  const [bySession, setBySession] = useState<Record<string, DepositionAnnotation[]>>(() =>
    Object.fromEntries(sessions.map((s) => [s.key, s.saved]))
  );
  const [activeAnnId, setActiveAnnId] = useState<string | null>(null);

  const scan = useAnnotationScan(active?.name ?? '', active?.runs ?? [], !readOnly);

  // Fold scanned candidates into the editable list once the scan resolves — syncing async
  // scan results into local state the user then edits (merge preserves existing edits + selection).
  useEffect(() => {
    if (!scan.data || !active) return;
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setBySession((prev) => ({
      ...prev,
      [active.key]: mergeAnnotations(scan.data.annotations, prev[active.key] ?? []),
    }));
  }, [scan.data, active]);
  // "Scanning" during the initial read, a re-scan submit, or while a job the server marks `pending`
  // is running (covers both the Re-scan click and a Sources pre-warm, #1154). A missing file
  // (scanned=false, not pending) means "no scan yet" and a failed job clears pending — either way
  // we stop, so the spinner never outlives the job. `pending` is the single source of truth.
  const [rescanning, setRescanning] = useState(false);
  const [rescanError, setRescanError] = useState<string | null>(null);
  const scanning = scan.isPending || rescanning || (!!scan.data?.pending && !scan.data?.scanned);

  // TEMP (#1154 tuning): log copick-scan wall-clock per session/runs to the console. Remove before merge.
  const scanTimerRef = useRef<{ session: string; t: number } | null>(null);
  useEffect(() => {
    if (!active) return;
    const cur = scanTimerRef.current;
    if (scanning && (!cur || cur.session !== active.name)) {
      scanTimerRef.current = { session: active.name, t: Date.now() };
      console.log(
        `[copick-scan] START ${active.name} runs=[${active.runs.join(', ')}] @ ${new Date().toLocaleTimeString()}`
      );
    } else if (!scanning && cur && cur.session === active.name) {
      const secs = ((Date.now() - cur.t) / 1000).toFixed(1);
      const anns = scan.data?.annotations ?? [];
      const by = (k: string) => anns.filter((a) => a.copick_kind === k).length;
      console.log(
        `[copick-scan] DONE  ${active.name} runs=[${active.runs.join(', ')}] @ ${new Date().toLocaleTimeString()} ` +
          `(${secs}s on-screen) — scanned=${!!scan.data?.scanned} ` +
          `picks=${by('picks')} segs=${by('segmentations')} meshes=${by('meshes')}` +
          (scan.data?.error ? ` ERROR=${scan.data.error}` : '')
      );
      scanTimerRef.current = null;
    }
  }, [scanning, scan.data, active]);

  const handleRescan = useCallback(async () => {
    if (!active || active.runs.length === 0) return;
    setRescanning(true);
    setRescanError(null);
    try {
      await rescanCopick(active.name, active.runs);
      // Re-read scan.json: the trigger wrote the pending marker, which now drives polling + spinner.
      await queryClient.invalidateQueries({ queryKey: ['copick-scan', active.name, [...active.runs].sort()] });
    } catch {
      setRescanError('Couldn’t start the scan. Try again.');
    } finally {
      setRescanning(false);
    }
  }, [active, queryClient]);

  const save = useCallback(
    async (state: Record<string, DepositionAnnotation[]>) => {
      const targets = sessions.filter((s) => s.id);
      const responses = await Promise.all(
        targets.map((s) =>
          updateSession(s.id as number, {
            annotations: (state[s.key] ?? []).filter((a) => a.is_selected).map(stripIncompleteLinks),
          })
        )
      );
      setBySession((prev) => {
        let changed = false;
        const next = { ...prev };
        targets.forEach((s, i) => {
          const cur = prev[s.key];
          if (!cur) return;
          const merged = mergeServerIds(cur, responses[i]?.annotations ?? []);
          if (merged !== cur) {
            next[s.key] = merged;
            changed = true;
          }
        });
        return changed ? next : prev;
      });
      queryClient.invalidateQueries({ queryKey: depositionKeys.dataset(dataset.id) });
    },
    [dataset.id, queryClient, sessions]
  );

  const { status, lastSavedAt, saveNow } = useDraftAutoSave(bySession, save, { enabled: !readOnly });
  useEffect(() => {
    reportSave?.({ status, lastSavedAt, saveNow });
  }, [status, lastSavedAt, saveNow, reportSave]);

  const list = useMemo(() => bySession[active?.key ?? ''] ?? [], [bySession, active]);
  const activeAnn = list.find((a) => annId(a) === activeAnnId) ?? null;

  useEffect(() => {
    if (list.length === 0 || (activeAnnId && list.some((a) => annId(a) === activeAnnId))) return;
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setActiveAnnId(annId(list.find((a) => a.is_selected) ?? list[0]));
  }, [activeAnnId, list]);

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
    setActiveAnnId(id); // selecting a row also opens its metadata form on the right
  };

  const setAll = (selected: boolean) => {
    if (!active) return;
    setBySession((prev) => ({
      ...prev,
      [active.key]: (prev[active.key] ?? []).map((a) => ({ ...a, is_selected: selected })),
    }));
  };

  // Drop a stale row (saved, but no longer in the latest scan) from the deposit.
  const removeStale = (id: string) => {
    if (!active) return;
    setBySession((prev) => ({
      ...prev,
      [active.key]: (prev[active.key] ?? []).filter((a) => annId(a) !== id),
    }));
    if (activeAnnId === id) setActiveAnnId(null);
  };

  if (sessions.length === 0) {
    return <Alert severity="info">Add sessions with copick configs on Sources first.</Alert>;
  }

  const needCount = list.filter(annotationNeedsMetadata).length;

  const staleIds = staleAnnotationIds(list, scan.data);

  const scanAlerts = (
    <>
      {scanning && (
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1.5 }}>
          <CircularProgress size={14} />
          <Typography variant="caption" color="text.secondary">
            Scanning new configs…
          </Typography>
        </Box>
      )}
      {scan.isError && (
        <Alert severity="warning" sx={{ mb: 1.5 }}>
          Copick scan unavailable - showing saved annotations only.
        </Alert>
      )}
      {!scan.isError && !!scan.data && scan.data.error && (
        <Alert severity="error" sx={{ mb: 1.5 }}>
          Scan failed - {scan.data.error}.
        </Alert>
      )}
      {!scan.isError &&
        !!scan.data &&
        !scan.data.scanned &&
        !scan.data.pending &&
        !scan.data.error &&
        scan.data.annotations.length === 0 && (
          <Alert severity="info" sx={{ mb: 1.5 }}>
            No scan yet - click Re-scan copick.
          </Alert>
        )}
      {!scan.isError && !!scan.data && !scan.data.scanned && scan.data.annotations.length > 0 && (
        <Alert severity="info" sx={{ mb: 1.5 }}>
          Some configs aren’t scanned yet - showing what’s available.
        </Alert>
      )}
    </>
  );

  let body: ReactNode;
  if ((active?.runs.length ?? 0) === 0) {
    body = <Alert severity="info">No copick configs selected on Sources.</Alert>;
  } else if (scanning && list.length === 0) {
    // Full spinner ONLY when there's nothing to show yet. If we already have annotations (e.g. a
    // config was just added on top of scanned ones), keep them on screen with an inline indicator.
    body = (
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, py: 4, justifyContent: 'center' }}>
        <CircularProgress size={20} />
        <Typography variant="body2" color="text.secondary">
          Scanning copick configs…
        </Typography>
      </Box>
    );
  } else if (list.length === 0) {
    // Nothing to list or edit → no split layout (a divider + empty right pane just reads as broken).
    body = (
      <Box>
        {scanAlerts}
        {!!scan.data?.scanned && !scan.data.error && (
          <Typography variant="body2" color="text.secondary">
            No annotations found in the selected copick configs.
          </Typography>
        )}
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
          {scanAlerts}
          <AnnotationList
            annotations={list}
            activeId={activeAnnId}
            onActivate={setActiveAnnId}
            onToggle={toggle}
            onSetAll={setAll}
            onRemove={removeStale}
            staleIds={staleIds}
            readOnly={readOnly}
          />
        </Box>

        <Box sx={{ position: { md: 'sticky' }, top: 0, alignSelf: 'start' }}>
          {activeAnn && (
            <>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mb: 2 }}>
                <Typography variant="subtitle1" sx={{ fontWeight: 700, fontFamily: 'monospace' }}>
                  {activeAnn.copick_ref}
                </Typography>
                <Chip label={activeAnn.copick_kind} size="small" />
              </Box>
              <AnnotationMetadataForm
                key={annId(activeAnn)}
                annotation={activeAnn}
                onChange={patchActive}
                readOnly={readOnly}
              />
            </>
          )}
        </Box>
      </Box>
    );
  }

  return (
    <Box>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        Select annotations to deposit, then fill in metadata for each.
      </Typography>

      <Box
        sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 2, mb: 2 }}
      >
        {sessions.length > 1 ? (
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
            sx={{ flexWrap: 'wrap' }}
          >
            {sessions.map((s) => (
              <ToggleButton key={s.key} value={s.key} sx={{ textTransform: 'none' }}>
                {s.name || 'Session'}
              </ToggleButton>
            ))}
          </ToggleButtonGroup>
        ) : (
          <Box />
        )}
        {(active?.runs.length ?? 0) > 0 && !readOnly && (
          <Button size="small" variant="outlined" onClick={handleRescan} disabled={scanning || rescanning}>
            {scanning || rescanning ? 'Scanning…' : 'Re-scan copick'}
          </Button>
        )}
      </Box>

      {rescanError && (
        <Alert severity="error" sx={{ mb: 1.5 }} onClose={() => setRescanError(null)}>
          {rescanError}
        </Alert>
      )}

      {body}

      {staleIds.size > 0 && (
        <Alert severity="warning" sx={{ mt: 2 }}>
          {staleIds.size} annotation{staleIds.size === 1 ? '' : 's'} no longer in the scan - remove with trash.
        </Alert>
      )}

      {needCount > 0 && (
        <Alert severity="warning" sx={{ mt: 2 }}>
          {needCount} selected annotation{needCount === 1 ? '' : 's'} need a name and ontology ID.
        </Alert>
      )}
    </Box>
  );
}
