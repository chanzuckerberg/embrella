import { useQuery } from '@tanstack/react-query';

import { normalizeScan, type ScannedAnnotation } from '../components/annotations/scan';
import { scanCopickAnnotations } from '../services/depositionApi';

const STALE = 5 * 60 * 1000;

/** Scan a session's selected copick runs for picks/segmentations/meshes (SSH — slow). */
export function useAnnotationScan(sessionName: string, runs: string[], enabled = true) {
  const sortedRuns = [...runs].sort();
  return useQuery<ScannedAnnotation[]>({
    queryKey: ['copick-scan', sessionName, sortedRuns],
    queryFn: async () => normalizeScan(await scanCopickAnnotations(sessionName, sortedRuns)),
    enabled: enabled && !!sessionName && sortedRuns.length > 0,
    staleTime: STALE,
    retry: false, // the scan is a slow SSH call — don't retry-loop, surface errors fast
  });
}
