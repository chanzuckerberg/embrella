import { useQuery } from '@tanstack/react-query';

import {
  type AnnotatedCount,
  getAnnotatedCount,
  getCopickRunObjects,
  getTomogramCount,
  listCopickRuns,
  listMsiSessions,
  listPlanRuns,
} from '../services/depositionApi';
import type { CopickRunOption } from '../types';

const sourceKeys = {
  msiSessions: ['deposition', 'sources', 'msi-sessions'] as const,
  planRuns: (plan: string, session: string) => ['deposition', 'sources', 'plan-runs', plan, session] as const,
  copickRuns: (session: string) => ['deposition', 'sources', 'copick-runs', session] as const,
  copickRunObjects: (session: string, run: string) =>
    ['deposition', 'sources', 'copick-run-objects', session, run] as const,
  tomoCount: (session: string, run: string) => ['deposition', 'sources', 'tomo-count', session, run] as const,
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

/** Total tomograms for a chosen session + AreTomo run. */
export function useTomogramCount(sessionName: string, aretomoRun: string) {
  return useQuery<number>({
    queryKey: sourceKeys.tomoCount(sessionName, aretomoRun),
    queryFn: () => getTomogramCount(sessionName, aretomoRun),
    enabled: sessionName.trim().length > 0 && aretomoRun.trim().length > 0,
    staleTime: STALE,
  });
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

export function useAnnotatedCount(sessionName: string, runs: string[], enabled: boolean) {
  return useQuery<AnnotatedCount>({
    queryKey: sourceKeys.annotatedCount(sessionName, runs),
    queryFn: () => getAnnotatedCount(sessionName, runs),
    enabled: enabled && sessionName.trim().length > 0 && runs.length > 0,
    staleTime: STALE,
    refetchInterval: (query) => annotatedRefetchInterval(query.state.data, query.state.status === 'error'),
  });
}
