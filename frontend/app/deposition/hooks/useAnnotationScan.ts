import { keepPreviousData, useQuery } from '@tanstack/react-query';

import { normalizeScan, type ScannedAnnotation } from '../components/annotations/scan';
import { scanCopickAnnotations } from '../services/depositionApi';

const STALE = 5 * 60 * 1000;
const POLL = 8 * 1000;

export interface AnnotationScan {
  scanned: boolean;
  pending: boolean;
  error?: string;
  annotations: ScannedAnnotation[];
}

/**
 * Read the cached copick scan.json for a session's selected runs.
 */
export function useAnnotationScan(sessionName: string, runs: string[], enabled = true) {
  const sortedRuns = [...runs].sort();
  return useQuery<AnnotationScan>({
    queryKey: ['copick-scan', sessionName, sortedRuns],
    queryFn: async () => {
      const res = await scanCopickAnnotations(sessionName, sortedRuns);
      return {
        scanned: res.scanned ?? false,
        pending: res.pending ?? false,
        error: res.error,
        annotations: normalizeScan(res),
      };
    },
    enabled: enabled && !!sessionName && sortedRuns.length > 0,
    staleTime: STALE,
    // Adding/removing a config changes the query key; keep the prior result on screen during the
    // refetch, so the annotations list doesn't flash empty.
    placeholderData: keepPreviousData,
    refetchInterval: (query) => {
      const data = query.state.data;
      return !data?.scanned && !!data?.pending ? POLL : false;
    },
    retry: false,
  });
}
