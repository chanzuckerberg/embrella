import { useQuery } from '@tanstack/react-query';

import { listCopickRuns, listMsiSessions, listPlanRuns } from '../services/depositionApi';
import type { CopickRunOption } from '../types';

const sourceKeys = {
  msiSessions: ['deposition', 'sources', 'msi-sessions'] as const,
  planRuns: (plan: string, session: string) => ['deposition', 'sources', 'plan-runs', plan, session] as const,
  copickRuns: (session: string) => ['deposition', 'sources', 'copick-runs', session] as const,
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
