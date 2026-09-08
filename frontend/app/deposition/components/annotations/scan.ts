import type { CopickKind, DepositionAnnotation } from '../../types';

/** A copick annotation discovered by the cluster scan (before the user adds metadata). */
export interface ScannedAnnotation {
  copick_kind: CopickKind;
  copick_ref: string; // "<object>:<user_id>/<session_id>"
  object_name: string;
  count?: number | null; // total_count — picks only; 0 for segmentations/meshes
}

/**
 * A row in an `annotations` section, already aggregated by (copick_kind, copick_ref)
 * by the copick scan job (#1130): copick_ref is pre-computed on the cluster, and
 * counts are rolled up (run_count = # runs carrying it, total_count = summed points).
 */
interface RawRow {
  copick_ref: string;
  object_name?: string | null;
  run_count?: number;
  total_count?: number;
}

/** Raw `annotations` block from GET /copick/v1/projects/<session>/<run>/?scan=true. */
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

/** A selected annotation is incomplete until it has the portal-required name + ontology id. */
export function annotationNeedsMetadata(a: DepositionAnnotation): boolean {
  return !!a.is_selected && (!a.object_name?.trim() || !a.object_id?.trim());
}

export function stripIncompleteLinks(a: DepositionAnnotation): DepositionAnnotation {
  if (!a.method_links?.length) return a;
  const links = a.method_links.filter((l) => l.link?.trim());
  return links.length === a.method_links.length ? a : { ...a, method_links: links };
}

const annKey = (kind: CopickKind, ref: string) => `${kind}::${ref}`;

/** Copy server ids onto local rows after save so the next autosave updates instead of recreating. Match annotations by kind/ref and links by type+url - a row edited mid-save won't match, so we leave it id-less. Same array back if nothing changed, to avoid kicking autosave again. */
export function mergeServerIds(local: DepositionAnnotation[], saved: DepositionAnnotation[]): DepositionAnnotation[] {
  const savedByRef = new Map(saved.map((a) => [annKey(a.copick_kind, a.copick_ref), a]));
  let changed = false;
  const out = local.map((a) => {
    const s = savedByRef.get(annKey(a.copick_kind, a.copick_ref));
    if (!s) return a;
    let merged = a;
    if (a.id == null && s.id != null) merged = { ...merged, id: s.id };
    const savedLinks = s.method_links;
    if (a.method_links?.length && savedLinks?.length) {
      let linksChanged = false;
      const links = a.method_links.map((l) => {
        if (l.id != null) return l;
        const m = savedLinks.find((sl) => sl.link_type === l.link_type && sl.link === l.link);
        if (!m || m.id == null) return l;
        linksChanged = true;
        return { ...l, id: m.id };
      });
      if (linksChanged) merged = { ...merged, method_links: links };
    }
    if (merged !== a) changed = true;
    return merged;
  });
  return changed ? out : local;
}

/**
 * Merge scanned candidates with saved annotations by (copick_kind, copick_ref):
 * - scanned + saved  -> saved metadata + is_selected win (user edits preserved)
 * - scanned only     -> fresh candidate, is_selected=false
 * - saved only (no longer scanned) -> kept so user data isn't lost; stale UX is #868
 */
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
