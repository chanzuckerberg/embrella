'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { Alert, Box, CircularProgress } from '@mui/material';

import { getMsiSessionId, updateDataset, uploadSubsetCsv } from '../../services/depositionApi';
import { depositionKeys } from '../../queryKeys';
import { useDraftAutoSave } from '../../hooks/useDraftAutoSave';
import { useMsiSessions } from '../../hooks/useSources';
import { SourcesTable, type SourceRow } from '../../components/SourcesTable';
import type { StepProps } from '../wizardTypes';
import type { Dataset, TomogramSubsetMode } from '../../types';

interface SourcesState {
  rows: SourceRow[];
  subsetMode: TomogramSubsetMode;
}

export function sourceValidationError(rows: SourceRow[]): string | null {
  if (rows.some((row) => row.id != null && !row.msi_session_name.trim())) {
    return 'Select an imaging session or use Remove session to delete it. Your changes have not been saved.';
  }
  const names = rows.map((row) => row.msi_session_name.trim()).filter(Boolean);
  if (new Set(names).size !== names.length) {
    return 'Each imaging session can only be selected once. Your changes have not been saved.';
  }
  return null;
}

function toRows(dataset: Dataset): SourceRow[] {
  return (dataset.sessions ?? []).map((s, i) => ({
    key: `s-${s.id ?? i}`,
    id: s.id,
    msi_session: s.msi_session ?? null,
    msi_session_name: s.msi_session_name ?? '',
    aretomo_run_name: s.aretomo_run_name ?? '',
    denoise_run_name: s.denoise_run_name ?? '',
    subset_csv_path: s.subset_csv_path ?? '',
    subset_selection: s.subset_selection ?? undefined,
    subset_filename: s.subset_filename || undefined,
    subset_input_mode: s.subset_csv_path ? 'path' : 'upload',
    selected_copick_runs: Array.isArray(s.selected_copick_runs) ? (s.selected_copick_runs as string[]) : [],
  }));
}

export function SourcesStep({ dataset, reportSave, readOnly: readOnlyProp }: StepProps) {
  const queryClient = useQueryClient();
  const readOnly = readOnlyProp || dataset.status !== 'draft';
  const [rows, setRows] = useState<SourceRow[]>(() => toRows(dataset));
  const [subsetMode, setSubsetMode] = useState<TomogramSubsetMode>(dataset.tomogram_subset_mode ?? 'all');
  const sessions = useMsiSessions();

  const save = useCallback(
    async (state: SourcesState) => {
      const error = sourceValidationError(state.rows);
      if (error) throw new Error(error);
      const complete = state.rows.filter((r) => r.msi_session_name.trim());
      const payload = await Promise.all(
        complete.map(async (r) => ({
          ...(r.id ? { id: r.id } : {}),
          msi_session: r.msi_session ?? (await getMsiSessionId(r.msi_session_name)),
          aretomo_run_name: r.aretomo_run_name,
          denoise_run_name: r.denoise_run_name,
          subset_csv_path: r.subset_csv_path,
          subset_selection: r.subset_selection ?? null,
          subset_filename: r.subset_filename ?? '',
          selected_copick_runs: r.selected_copick_runs,
        }))
      );
      const updated = await updateDataset(dataset.id, {
        sessions: payload as unknown as Dataset['sessions'],
        tomogram_subset_mode: state.subsetMode,
      });
      queryClient.setQueryData(depositionKeys.dataset(dataset.id), updated);
      queryClient.invalidateQueries({ queryKey: [...depositionKeys.all, 'submissions'] });

      const byName = new Map((updated.sessions ?? []).map((s) => [s.msi_session_name, s]));
      setRows((prev) =>
        prev.map((r) => {
          const s = byName.get(r.msi_session_name);
          if (s && (r.id !== s.id || r.msi_session !== s.msi_session)) {
            return { ...r, id: s.id, msi_session: s.msi_session };
          }
          return r;
        })
      );
    },
    [dataset.id, queryClient]
  );

  const validationError = sourceValidationError(rows);
  const formState = useMemo<SourcesState>(() => ({ rows, subsetMode }), [rows, subsetMode]);
  const { status, lastSavedAt, saveNow } = useDraftAutoSave(formState, save, { enabled: !readOnly });
  useEffect(() => {
    reportSave?.({ status, lastSavedAt, saveNow });
  }, [status, lastSavedAt, saveNow, reportSave]);

  const handleUploadSubset = async (row: SourceRow, file: File) => {
    if (!row.id) return;
    // Upload mode stores the parsed selection in the DB, keep the filename for display only.
    const { subset_selection } = await uploadSubsetCsv(row.id, file);
    setRows((prev) =>
      prev.map((r) =>
        r.key === row.key ? { ...r, subset_selection, subset_filename: file.name, subset_csv_path: '' } : r
      )
    );
  };

  return (
    <Box>
      {validationError && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {validationError}
        </Alert>
      )}
      {sessions.isError && (
        <Alert severity="error" sx={{ mb: 2 }}>
          Could not load the list of sessions. Try reloading the page.
        </Alert>
      )}
      {sessions.isPending ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 6 }}>
          <CircularProgress />
        </Box>
      ) : (
        <SourcesTable
          rows={rows}
          sessionOptions={sessions.data ?? []}
          subsetMode={subsetMode}
          readOnly={readOnly}
          onChange={setRows}
          onSubsetModeChange={setSubsetMode}
          onUploadSubset={handleUploadSubset}
        />
      )}
    </Box>
  );
}
