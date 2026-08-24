import type { CopickKind, DepositionAnnotation } from '../../types';

/** A copick annotation discovered by the cluster scan (before the user adds metadata). */
export interface ScannedAnnotation {
  copick_kind: CopickKind;
  copick_ref: string; // "<object>:<user_id>/<session_id>"
  object_name: string;
  run_name: string;
  count?: number | null;
}

interface RawPick {
  run_name: string;
  object_name?: string | null;
  user_id?: string;
  session_id?: string;
  count?: number | null;
}
interface RawSeg {
  run_name: string;
  name?: string | null;
  user_id?: string;
  session_id?: string;
}
interface RawMesh {
  run_name: string;
  object_name?: string | null;
  user_id?: string;
  session_id?: string;
}

/** Raw `annotations` block from GET /copick/v1/projects/<session>/<run>/?scan=true. */
export interface ScanResult {
  picks?: RawPick[];
  segmentations?: RawSeg[];
  meshes?: RawMesh[];
}

/** copick_ref is the stable identity of an annotation: "<object>:<user_id>/<session_id>". */
function makeRef(object: string | null | undefined, userId?: string, sessionId?: string): string {
  return `${object ?? ''}:${userId ?? ''}/${sessionId ?? ''}`;
}

export function normalizeScan(scan: ScanResult): ScannedAnnotation[] {
  const out: ScannedAnnotation[] = [];
  for (const p of scan.picks ?? []) {
    out.push({
      copick_kind: 'picks',
      copick_ref: makeRef(p.object_name, p.user_id, p.session_id),
      object_name: p.object_name ?? '',
      run_name: p.run_name,
      count: p.count ?? null,
    });
  }
  for (const s of scan.segmentations ?? []) {
    out.push({
      copick_kind: 'segmentations',
      copick_ref: makeRef(s.name, s.user_id, s.session_id),
      object_name: s.name ?? '',
      run_name: s.run_name,
    });
  }
  for (const m of scan.meshes ?? []) {
    out.push({
      copick_kind: 'meshes',
      copick_ref: makeRef(m.object_name, m.user_id, m.session_id),
      object_name: m.object_name ?? '',
      run_name: m.run_name,
    });
  }
  return out;
}

/** A selected annotation is incomplete until it has the portal-required name + ontology id. */
export function annotationNeedsMetadata(a: DepositionAnnotation): boolean {
  return !!a.is_selected && (!a.object_name?.trim() || !a.object_id?.trim());
}

const annKey = (kind: CopickKind, ref: string) => `${kind}::${ref}`;

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
