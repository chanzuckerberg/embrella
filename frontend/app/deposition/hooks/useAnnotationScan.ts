import { useQuery } from '@tanstack/react-query';

import { normalizeScan, type ScannedAnnotation } from '../components/annotations/scan';
import { scanCopickAnnotations } from '../services/depositionApi';

const STALE = 5 * 60 * 1000;

export interface AnnotationScan {
  scanned: boolean; // false when no completed scan.json exists yet for the selected runs
  annotations: ScannedAnnotation[];
}

/** Read the cached copick scan.json for a session's selected runs. */
export function useAnnotationScan(sessionName: string, runs: string[], enabled = true) {
  const sortedRuns = [...runs].sort();
  return useQuery<AnnotationScan>({
    queryKey: ['copick-scan', sessionName, sortedRuns],
    queryFn: async () => {
      const res = await scanCopickAnnotations(sessionName, sortedRuns);
      return { scanned: res.scanned ?? false, annotations: normalizeScan(res) };
    },
    enabled: enabled && !!sessionName && sortedRuns.length > 0,
    staleTime: STALE,
    retry: false, // reads are cheap; surface errors instead of retry-looping
  });
}
