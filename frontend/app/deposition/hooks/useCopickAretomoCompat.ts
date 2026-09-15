import { useQuery } from '@tanstack/react-query';

import { fetchCopickAretomoCompat, type CopickAretomoCompat } from '../services/depositionApi';

const STALE = 5 * 60 * 1000;

/**
   check whether the annotated copick runs are part of the deposited AreTomo run.
 */
export function useCopickAretomoCompat(sessionName: string, aretomoRun: string, copickRuns: string[], enabled = true) {
  const sortedRuns = [...copickRuns].sort();
  return useQuery<CopickAretomoCompat>({
    queryKey: ['copick-aretomo-compat', sessionName, aretomoRun, sortedRuns],
    queryFn: () => fetchCopickAretomoCompat(sessionName, aretomoRun, sortedRuns),
    enabled: enabled && !!sessionName && !!aretomoRun && sortedRuns.length > 0,
    staleTime: STALE,
    retry: false,
  });
}
