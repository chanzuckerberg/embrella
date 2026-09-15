import type { CopickKind, DepositionAnnotation } from '../../types';

export interface ScannedAnnotation {
  copick_kind: CopickKind;
  copick_ref: string; // "<object>:<user_id>/<session_id>"
  object_name: string;
  object_id: string; // ontology id from the config's pickable_objects
  count?: number | null; // total_count — picks only; 0 for segmentations/meshes
}

interface RawRow {
  copick_ref: string;
  object_name?: string | null;
  object_id?: string | null;
  run_count?: number;
  total_count?: number;
}

export interface ScanResult {
  scanned?: boolean;
  // A scan job is running (or was just triggered) - distinct from a missing file (never scanned).
  pending?: boolean;
  // The last job failed to enumerate (env/config/run error) — distinct from "never scanned".
  error?: string;
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
        object_id: r.object_id ?? '',
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

/** Ids (kind::ref) of saved rows a *completed* scan no longer returns stale . */
export function staleAnnotationIds(
  list: DepositionAnnotation[],
  scan: { scanned: boolean; annotations: ScannedAnnotation[] } | null | undefined
): Set<string> {
  if (!scan?.scanned) return new Set();
  const present = new Set(scan.annotations.map((a) => annKey(a.copick_kind, a.copick_ref)));
  return new Set(list.map((a) => annKey(a.copick_kind, a.copick_ref)).filter((key) => !present.has(key)));
}

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
 * Merge scanned candidates into saved rows by copick_kind::copick_ref:
 * - existing saved row -> fill object_name/object_id from the scan only where the user hasn't set them
 * - scanned-only       -> appended as an unselected candidate
 * - saved-only (no longer scanned) -> kept in place (no data loss; stale UX is #868)
 * Saved order is preserved, and the SAME `saved` reference is returned when nothing changed — so a
 * re-fold from an unchanged scan poll produces no new state (which would otherwise retrigger autosave).
 */
export function mergeAnnotations(scanned: ScannedAnnotation[], saved: DepositionAnnotation[]): DepositionAnnotation[] {
  const scannedByKey = new Map<string, ScannedAnnotation>();
  for (const sc of scanned) {
    const k = annKey(sc.copick_kind, sc.copick_ref);
    if (!scannedByKey.has(k)) scannedByKey.set(k, sc); // same (kind, ref) across runs -> one identity
  }
  const savedKeys = new Set(saved.map((a) => annKey(a.copick_kind, a.copick_ref)));

  let changed = false;
  const out = saved.map((a) => {
    const sc = scannedByKey.get(annKey(a.copick_kind, a.copick_ref));
    if (!sc) return a;
    const object_name = a.object_name || sc.object_name;
    const object_id = a.object_id || sc.object_id;
    if (object_name === a.object_name && object_id === a.object_id) return a;
    changed = true;
    return { ...a, object_name, object_id };
  });
  for (const sc of scannedByKey.values()) {
    if (savedKeys.has(annKey(sc.copick_kind, sc.copick_ref))) continue;
    out.push({
      copick_kind: sc.copick_kind,
      copick_ref: sc.copick_ref,
      object_name: sc.object_name,
      object_id: sc.object_id,
      is_selected: false,
    });
    changed = true;
  }
  return changed ? out : saved;
}
