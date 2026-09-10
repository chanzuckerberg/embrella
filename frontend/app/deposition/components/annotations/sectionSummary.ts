import type { DepositionAnnotation } from '../../types';

// object_count is portal-derived at ingestion.
export function detailsFilled(a: DepositionAnnotation): number {
  let n = 0;
  if (a.object_state?.trim()) n += 1;
  if (a.object_description?.trim()) n += 1;
  return n;
}

export function methodFilled(a: DepositionAnnotation): number {
  let n = 0;
  if (a.annotation_method?.trim()) n += 1;
  if (a.annotation_software?.trim()) n += 1;
  return n;
}

export function linkCount(a: DepositionAnnotation): number {
  return a.method_links?.length ?? 0;
}

export function doiCount(a: DepositionAnnotation): number {
  return (a.annotation_publication ?? '')
    .split(',')
    .map((s) => s.trim())
    .filter(Boolean).length;
}

export function flagsSet(a: DepositionAnnotation): number {
  return (a.ground_truth_status ? 1 : 0) + (a.is_visualization_default ? 1 : 0);
}
