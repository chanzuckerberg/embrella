import { useQuery } from '@tanstack/react-query';

import { normalizeScan, type ScannedAnnotation } from '../components/annotations/scan';
import { scanCopickAnnotations } from '../services/depositionApi';

const STALE = 5 * 60 * 1000;
const POLL = 8 * 1000; // while a scan job is still running, re-read scan.json this often

export interface AnnotationScan {
  scanned: boolean; // false while a scan job is still pending for any selected run
  annotations: ScannedAnnotation[];
}

/**
 * Read the cached copick scan.json for a session's selected runs.
 *
 * `polling` should be true only while we're actively waiting on a scan job we just triggered
 * (re-scan click, or #1154 pre-warm). Otherwise scanned=false simply means "no scan has run yet"
 * — there's no job to wait for, so we must NOT poll (that would spin "Scanning…" forever).
 */
export function useAnnotationScan(sessionName: string, runs: string[], enabled = true, polling = false) {
  const sortedRuns = [...runs].sort();
  return useQuery<AnnotationScan>({
    queryKey: ['copick-scan', sessionName, sortedRuns],
    queryFn: async () => {
      const res = await scanCopickAnnotations(sessionName, sortedRuns);
      return { scanned: res.scanned ?? false, annotations: normalizeScan(res) };
    },
    enabled: enabled && !!sessionName && sortedRuns.length > 0,
    staleTime: STALE,
    // Re-read scan.json only while a triggered job is still finishing; stop once it's scanned.
    refetchInterval: (query) => (polling && !query.state.data?.scanned ? POLL : false),
    retry: false, // reads are cheap; surface errors instead of retry-looping
  });
}
