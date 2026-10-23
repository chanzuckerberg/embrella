import { queryOptions, useQueries, useQuery } from '@tanstack/react-query';

import {
  type AnnotatedCount,
  getAnnotatedCount,
  getCopickRunObjects,
  getDenoisedTomogramCount,
  getTomogramCount,
  listCopickRuns,
  listMsiSessions,
  listPlanRuns,
} from '../services/depositionApi';
import type { CopickRunOption, Dataset } from '../types';
import { rowSelected } from '../components/sources/counts';

const sourceKeys = {
  msiSessions: ['deposition', 'sources', 'msi-sessions'] as const,
  planRuns: (plan: string, session: string) => ['deposition', 'sources', 'plan-runs', plan, session] as const,
  copickRuns: (session: string) => ['deposition', 'sources', 'copick-runs', session] as const,
  copickRunObjects: (session: string, run: string) =>
    ['deposition', 'sources', 'copick-run-objects', session, run] as const,
  tomoCount: (session: string, run: string) => ['deposition', 'sources', 'tomo-count', session, run] as const,
  denoiseCount: (session: string, run: string) => ['deposition', 'sources', 'denoise-count', session, run] as const,
  annotatedCount: (session: string, runs: string[]) =>
    ['deposition', 'sources', 'annotated-count', session, runs.join(',')] as const,
};

const STALE = 5 * 60 * 1000;

export function useMsiSessions() {
  return useQuery<string[]>({
    queryKey: sourceKeys.msiSessions,
    queryFn: listMsiSessions,
    staleTime: STALE,
  });
}

export function usePlanRuns(planType: 'aretomo3' | 'denoiset', sessionName: string) {
  return useQuery<string[]>({
    queryKey: sourceKeys.planRuns(planType, sessionName),
    queryFn: () => listPlanRuns(planType, sessionName),
    enabled: sessionName.trim().length > 0,
    staleTime: STALE,
  });
}

export function useCopickRuns(sessionName: string) {
  return useQuery<CopickRunOption[]>({
    queryKey: sourceKeys.copickRuns(sessionName),
    queryFn: () => listCopickRuns(sessionName),
    enabled: sessionName.trim().length > 0,
    staleTime: STALE,
  });
}

function tomogramCountOptions(sessionName: string, aretomoRun: string) {
  return queryOptions({
    queryKey: sourceKeys.tomoCount(sessionName, aretomoRun),
    queryFn: () => getTomogramCount(sessionName, aretomoRun),
    enabled: sessionName.trim().length > 0 && aretomoRun.trim().length > 0,
    staleTime: STALE,
  });
}

function denoiseCountOptions(sessionName: string, run: string) {
  return queryOptions({
    queryKey: sourceKeys.denoiseCount(sessionName, run),
    queryFn: () => getDenoisedTomogramCount(sessionName, run),
    enabled: sessionName.trim().length > 0 && run.trim().length > 0,
    staleTime: STALE,
  });
}

export function useTomogramCount(sessionName: string, aretomoRun: string) {
  return useQuery(tomogramCountOptions(sessionName, aretomoRun));
}

export function useCopickRunObjects(sessionName: string, run: string, enabled: boolean) {
  return useQuery<string[]>({
    queryKey: sourceKeys.copickRunObjects(sessionName, run),
    queryFn: () => getCopickRunObjects(sessionName, run),
    enabled: enabled && sessionName.trim().length > 0 && run.trim().length > 0,
    staleTime: STALE,
  });
}

const ANNOTATED_POLL_MS = 5000;

export const annotatedRefetchInterval = (data: AnnotatedCount | undefined, isError = false): number | false =>
  !isError && data && !data.scanned ? ANNOTATED_POLL_MS : false;

function annotatedCountOptions(sessionName: string, runs: string[], enabled: boolean) {
  return queryOptions({
    queryKey: sourceKeys.annotatedCount(sessionName, runs),
    queryFn: () => getAnnotatedCount(sessionName, runs),
    enabled: enabled && sessionName.trim().length > 0 && runs.length > 0,
    staleTime: STALE,
    refetchInterval: (query) => annotatedRefetchInterval(query.state.data, query.state.status === 'error'),
  });
}

export function useAnnotatedCount(sessionName: string, runs: string[], enabled: boolean) {
  return useQuery(annotatedCountOptions(sessionName, runs, enabled));
}

export function useSelectedTomogramCount(dataset: Dataset): number | undefined {
  const sessions = dataset.sessions ?? [];
  const mode = dataset.tomogram_subset_mode ?? 'all';
  const aretomo = useQueries({
    queries: sessions.map((s) => tomogramCountOptions(s.msi_session_name ?? '', s.aretomo_run_name ?? '')),
  });
  const denoise = useQueries({
    queries: sessions.map((s) => denoiseCountOptions(s.msi_session_name ?? '', s.denoise_run_name ?? '')),
  });
  const annotated = useQueries({
    queries: sessions.map((s) =>
      annotatedCountOptions(s.msi_session_name ?? '', (s.selected_copick_runs ?? []) as string[], mode === 'annotated')
    ),
  });
  let total = 0;
  for (const [i, session] of sessions.entries()) {
    for (const [run, query] of [
      [session.aretomo_run_name, aretomo[i]],
      [session.denoise_run_name, denoise[i]],
    ] as const) {
      if (!run) continue;
      const sourceTotal = query.data;
      if (sourceTotal == null) return undefined;
      const selected = rowSelected(
        {
          subset_csv_path: session.subset_csv_path ?? '',
          subset_selection: session.subset_selection,
          tomogram_total: sourceTotal,
          tomogram_selected: annotated[i].data?.scanned ? annotated[i].data?.count : undefined,
        },
        mode
      );
      if (selected == null) return undefined;
      // Annotated counts can exceed a source's available volumes.
      total += Math.min(selected, sourceTotal);
    }
  }
  return total;
}
