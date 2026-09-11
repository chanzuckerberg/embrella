import { keepPreviousData, useQuery } from '@tanstack/react-query';

import { normalizeScan, type ScannedAnnotation } from '../components/annotations/scan';
import { scanCopickAnnotations } from '../services/depositionApi';

const STALE = 5 * 60 * 1000;
const POLL = 8 * 1000; // while a scan job is still running, re-read scan.json this often

export interface AnnotationScan {
  scanned: boolean; // false while a scan job is still pending for any selected run
  pending: boolean; // server marked a job running (trigger/pre-warm) — the sole poll/spinner signal
  error?: string; // the last job failed to enumerate (env/config/run error), so it's not just "unscanned"
  annotations: ScannedAnnotation[];
}

/**
 * Read the cached copick scan.json for a session's selected runs.
 *
 * `pending` (a server marker written when a job is triggered/pre-warmed and cleared when it finishes
 * or fails) is the ONLY "a job is running" signal — we poll while it's set. A missing file
 * (scanned=false, not pending) means "no scan has run yet"; a failed job is scanned=false + `error`,
 * not pending — either way we must NOT poll (nothing will land), so the spinner stops.
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
    // refetch instead of blanking to undefined, so the annotations list doesn't flash empty.
    placeholderData: keepPreviousData,
    refetchInterval: (query) => {
      const data = query.state.data;
      return !data?.scanned && !!data?.pending ? POLL : false;
    },
    retry: false, // reads are cheap; surface errors instead of retry-looping
  });
}
