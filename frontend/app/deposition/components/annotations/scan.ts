import type { CopickKind, DepositionAnnotation } from '../../types';

/** A copick annotation discovered by the cluster scan . */
export interface ScannedAnnotation {
  copick_kind: CopickKind;
  copick_ref: string; // "<object>:<user_id>/<session_id>"
  object_name: string;
  count?: number | null; // total_count - only for picks, 0 for segmentations/meshes
}

interface RawRow {
  copick_ref: string;
  object_name?: string | null;
  run_count?: number;
  total_count?: number;
}

export interface ScanResult {
  scanned?: boolean;
  picks?: RawRow[];
  segmentations?: RawRow[];
  meshes?: RawRow[];
  annotated_runs?: string[];
}

export function normalizeScan(scan: ScanResult): ScannedAnnotation[] {
  const sections: [CopickKind, RawRow[]][] = [
    ['picks', scan.picks ?? []],
    ['segmentations', scan.segmentations ?? []],
    ['meshes', scan.meshes ?? []],
  ];
  const out: ScannedAnnotation[] = [];
  for (const [kind, rows] of sections) {
    for (const r of rows) {
      out.push({
        copick_kind: kind,
        copick_ref: r.copick_ref,
        object_name: r.object_name ?? '',
        count: r.total_count ?? null,
      });
    }
  }
  return out;
}

export function annotationNeedsMetadata(a: DepositionAnnotation): boolean {
  return !!a.is_selected && (!a.object_name?.trim() || !a.object_id?.trim());
}

export function stripIncompleteLinks(a: DepositionAnnotation): DepositionAnnotation {
  if (!a.method_links?.length) return a;
  const links = a.method_links.filter((l) => l.link?.trim());
  return links.length === a.method_links.length ? a : { ...a, method_links: links };
}

const annKey = (kind: CopickKind, ref: string) => `${kind}::${ref}`;

export function mergeAnnotations(scanned: ScannedAnnotation[], saved: DepositionAnnotation[]): DepositionAnnotation[] {
  const savedByKey = new Map(saved.map((a) => [annKey(a.copick_kind, a.copick_ref), a]));
  const merged: DepositionAnnotation[] = [];
  const seen = new Set<string>();

  for (const sc of scanned) {
    const k = annKey(sc.copick_kind, sc.copick_ref);
    if (seen.has(k)) continue; // same (kind, ref) can appear across runs — one row per identity
    seen.add(k);
    const existing = savedByKey.get(k);
    merged.push(
      existing
        ? { ...existing, object_name: existing.object_name || sc.object_name }
        : { copick_kind: sc.copick_kind, copick_ref: sc.copick_ref, object_name: sc.object_name, is_selected: false }
    );
  }
  for (const a of saved) {
    if (!seen.has(annKey(a.copick_kind, a.copick_ref))) merged.push(a);
  }
  return merged;
}
