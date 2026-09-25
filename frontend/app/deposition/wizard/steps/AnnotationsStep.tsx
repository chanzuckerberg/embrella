'use client';

import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  LinearProgress,
  ToggleButton,
  ToggleButtonGroup,
  Tooltip,
  Typography,
} from '@mui/material';

import { rescanCopick, updateSession } from '../../services/depositionApi';
import { depositionKeys } from '../../queryKeys';
import { useDraftAutoSave } from '../../hooks/useDraftAutoSave';
import { useAnnotationScan } from '../../hooks/useAnnotationScan';
import { useCopickAretomoCompat } from '../../hooks/useCopickAretomoCompat';
import { AnnotationList, annId } from '../../components/annotations/AnnotationList';
import { AnnotationMetadataForm } from '../../components/annotations/AnnotationMetadataForm';
import {
  annotationNeedsMetadata,
  compatibleRuns,
  incompatibleRuns,
  mergeAnnotations,
  mergeServerIds,
  scanRunsByKey,
  staleAnnotationIds,
  stripIncompleteLinks,
} from '../../components/annotations/scan';
import type { Dataset, DepositionAnnotation } from '../../types';
import type { StepProps } from '../wizardTypes';

interface SessionRef {
  key: string;
  id?: number;
  name: string;
  aretomoRun: string;
  runs: string[];
  saved: DepositionAnnotation[];
}

function toSessionRefs(dataset: Dataset): SessionRef[] {
  return (dataset.sessions ?? []).map((s, i) => ({
    key: `ann-${s.id ?? i}`,
    id: s.id,
    name: s.msi_session_name ?? '',
    aretomoRun: s.aretomo_run_name ?? '',
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

  const [bySession, setBySession] = useState<Record<string, DepositionAnnotation[]>>(() =>
    Object.fromEntries(sessions.map((s) => [s.key, s.saved]))
  );
  const [activeAnnId, setActiveAnnId] = useState<string | null>(null);

  const scan = useAnnotationScan(active?.name ?? '', active?.runs ?? [], !readOnly);

  const compat = useCopickAretomoCompat(
    active?.name ?? '',
    active?.aretomoRun ?? '',
    active?.runs ?? [],
    !readOnly && !!scan.data?.scanned
  );

  useEffect(() => {
    if (!scan.data || !active) return;
    const key = active.key;
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setBySession((prev) => {
      const cur = prev[key] ?? [];
      const merged = mergeAnnotations(scan.data.annotations, cur);
      // Unchanged poll - same ref - no state churn, no autosave.
      return merged === cur ? prev : { ...prev, [key]: merged };
    });
  }, [scan.data, active]);
  const [rescanning, setRescanning] = useState(false);
  const [rescanError, setRescanError] = useState<string | null>(null);
  const scanning = scan.isPending || rescanning || (!!scan.data?.pending && !scan.data?.scanned);
  // Live "N of M runs" progress the scan job writes as it runs.
  const scanProgress = scan.data?.progressTotal
    ? { done: scan.data.progressDone ?? 0, total: scan.data.progressTotal }
    : null;
  const configCount = active?.runs.length ?? 0;
  const configLabel = `${configCount} copick config${configCount === 1 ? '' : 's'}`;

  const handleRescan = useCallback(async () => {
    if (!active || active.runs.length === 0) return;
    setRescanning(true);
    setRescanError(null);
    try {
      await rescanCopick(active.name, active.runs);
      // Re-read scan.json - the pending marker now drives polling + spinner.
      await queryClient.invalidateQueries({ queryKey: ['copick-scan', active.name, [...active.runs].sort()] });
      queryClient.invalidateQueries({ queryKey: ['copick-aretomo-compat', active.name] });
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

  const runsByKey = useMemo(() => scanRunsByKey(scan.data?.annotations ?? []), [scan.data]);
  const activeRuns = activeAnn ? (runsByKey.get(annId(activeAnn)) ?? []) : [];
  const activeCompatRuns = compatibleRuns(activeRuns, compat.data?.aretomo_runs);
  const activeIncompatRuns = incompatibleRuns(activeRuns, compat.data?.aretomo_runs);

  const runsChip = ((): ReactNode => {
    const total = activeRuns.length;
    if (total === 0) return null;
    // Compat still loading - plain count, no compat claim.
    if (!compat.data) return <Chip size="small" variant="outlined" label={`${total} run${total === 1 ? '' : 's'}`} />;
    if (activeCompatRuns.length === 0)
      return <Chip size="small" color="warning" label="no runs from this AreTomo run" />;
    const label = `${activeCompatRuns.length} of ${total} runs from this AreTomo run`;
    if (activeIncompatRuns.length === 0) return <Chip size="small" variant="outlined" label={label} />;
    const MAX = 20;
    const shown = activeIncompatRuns.slice(0, MAX).join(', ');
    const more = activeIncompatRuns.length > MAX ? ` +${activeIncompatRuns.length - MAX} more` : '';
    return (
      <Tooltip title={`Not from this AreTomo run: ${shown}${more}`}>
        <Chip size="small" color="warning" label={label} />
      </Tooltip>
    );
  })();

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

  // Drop a stale row (no longer in the scan) from the deposit.
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
            {scanProgress ? `Scanning… ${scanProgress.done} of ${scanProgress.total} runs` : `Scanning ${configLabel}…`}
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
    body = (
      <Box sx={{ py: 5, maxWidth: 380, mx: 'auto', textAlign: 'center' }}>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>
          {scanProgress
            ? `Scanning copick runs… ${scanProgress.done} of ${scanProgress.total}`
            : `Scanning ${configLabel}…`}
        </Typography>
        {scanProgress ? (
          <LinearProgress
            variant="determinate"
            value={scanProgress.total > 0 ? (scanProgress.done / scanProgress.total) * 100 : 0}
          />
        ) : (
          <LinearProgress />
        )}
      </Box>
    );
  } else if (list.length === 0) {
    body = (
      <Box>
        {scanAlerts}
        {!!scan.data?.scanned && !scan.data.error && (
          <Alert severity="info">No annotations found in the selected copick configs.</Alert>
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
          alignItems: 'stretch',
          flex: { md: 1 },
          minHeight: { md: 240 },
        }}
      >
        <Box
          sx={{
            display: 'flex',
            flexDirection: 'column',
            minHeight: 0,
            borderRight: { md: '1px solid' },
            borderColor: { md: 'divider' },
            pr: { md: 2 },
          }}
        >
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

        <Box sx={{ minHeight: 0, overflowY: { md: 'auto' } }}>
          {activeAnn && (
            <>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mb: 2, flexWrap: 'wrap' }}>
                <Typography variant="subtitle1" sx={{ fontWeight: 700, fontFamily: 'monospace' }}>
                  {activeAnn.copick_ref}
                </Typography>
                <Chip label={activeAnn.copick_kind} size="small" />
                {runsChip}
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
    <Box
      sx={{
        display: 'flex',
        flexDirection: 'column',
        flex: 1,
        minHeight: 0,
        '& > :not(:last-child)': { flexShrink: 0 },
      }}
    >
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
          {needCount} selected annotation{needCount === 1 ? ' is' : 's are'} incomplete (name + ontology ID required).
        </Alert>
      )}
    </Box>
  );
}
