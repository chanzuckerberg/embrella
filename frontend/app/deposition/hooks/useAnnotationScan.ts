import { useQuery } from '@tanstack/react-query';

import { normalizeScan, type ScannedAnnotation } from '../components/annotations/scan';
import { scanCopickAnnotations } from '../services/depositionApi';

const STALE = 5 * 60 * 1000;
const POLL = 8 * 1000;

export interface AnnotationScan {
  scanned: boolean;
  pending: boolean;
  error?: string;
  progressDone?: number;
  progressTotal?: number;
  annotations: ScannedAnnotation[];
}

/** Read the cached copick scan.json for a session's selected runs. */
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
        progressDone: res.progress_done,
        progressTotal: res.progress_total,
        annotations: normalizeScan(res),
      };
    },
    enabled: enabled && !!sessionName && sortedRuns.length > 0,
    staleTime: STALE,
    // Keep the prior result only within the SAME session (no empty flash on add/remove config);
    // dropped on a session switch so one session's rows never leak into another's draft.
    placeholderData: (prev, prevQuery) => (prevQuery?.queryKey[1] === sessionName ? prev : undefined),
    refetchInterval: (query) => {
      const data = query.state.data;
      return !data?.scanned && !!data?.pending ? POLL : false;
    },
    retry: false,
  });
}
