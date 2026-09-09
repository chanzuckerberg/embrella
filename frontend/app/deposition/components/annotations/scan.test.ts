import type { DepositionAnnotation } from '../../types';
import { annotationNeedsMetadata, mergeAnnotations, normalizeScan, type ScannedAnnotation } from './scan';

describe('annotationNeedsMetadata', () => {
  const sel = (o: Partial<DepositionAnnotation>): DepositionAnnotation => ({
    copick_kind: 'picks',
    copick_ref: 'x:u/1',
    is_selected: true,
    ...o,
  });
  it('is false when unselected', () => {
    expect(annotationNeedsMetadata({ ...sel({}), is_selected: false })).toBe(false);
  });
  it('is true when selected but missing name or id', () => {
    expect(annotationNeedsMetadata(sel({ object_name: '', object_id: 'GO:1' }))).toBe(true);
    expect(annotationNeedsMetadata(sel({ object_name: 'VLP', object_id: '' }))).toBe(true);
  });
  it('is false when selected and both present', () => {
    expect(annotationNeedsMetadata(sel({ object_name: 'VLP', object_id: 'GO:1' }))).toBe(false);
  });
});

describe('normalizeScan', () => {
  it('maps the aggregated picks/segmentations/meshes rows through copick_ref + total_count', () => {
    const out = normalizeScan({
      scanned: true,
      picks: [{ copick_ref: 'VLP:relion/2', object_name: 'VLP', run_count: 3, total_count: 12345 }],
      segmentations: [{ copick_ref: 'membrane:auto/1', object_name: 'membrane', run_count: 1, total_count: 0 }],
      meshes: [{ copick_ref: 'VLP_shells:auto/1', object_name: 'VLP_shells', run_count: 1, total_count: 0 }],
    });
    expect(out).toEqual([
      { copick_kind: 'picks', copick_ref: 'VLP:relion/2', object_name: 'VLP', count: 12345 },
      { copick_kind: 'segmentations', copick_ref: 'membrane:auto/1', object_name: 'membrane', count: 0 },
      { copick_kind: 'meshes', copick_ref: 'VLP_shells:auto/1', object_name: 'VLP_shells', count: 0 },
    ]);
  });

  it('is safe on empty/partial input', () => {
    expect(normalizeScan({})).toEqual([]);
    expect(normalizeScan({ picks: [] })).toEqual([]);
  });
});

describe('mergeAnnotations', () => {
  const scanned: ScannedAnnotation[] = [
    { copick_kind: 'picks', copick_ref: 'VLP:relion/2', object_name: 'VLP' },
    { copick_kind: 'picks', copick_ref: 'GroEL:upload/1', object_name: 'GroEL' },
  ];

  it('carries saved metadata + is_selected onto matching scanned items', () => {
    const saved: DepositionAnnotation[] = [
      { copick_kind: 'picks', copick_ref: 'VLP:relion/2', object_name: 'VLP', is_selected: true, object_count: 12345 },
    ];
    const merged = mergeAnnotations(scanned, saved);
    const vlp = merged.find((a) => a.copick_ref === 'VLP:relion/2')!;
    expect(vlp.is_selected).toBe(true);
    expect(vlp.object_count).toBe(12345);
  });

  it('marks scanned-only items as unselected candidates', () => {
    const merged = mergeAnnotations(scanned, []);
    expect(merged).toHaveLength(2);
    expect(merged.every((a) => a.is_selected === false)).toBe(true);
  });

  it('dedupes the same (kind, ref) appearing across multiple runs', () => {
    const dupes: ScannedAnnotation[] = [
      { copick_kind: 'picks', copick_ref: 'VLP:relion/2', object_name: 'VLP' },
      { copick_kind: 'picks', copick_ref: 'VLP:relion/2', object_name: 'VLP' },
    ];
    expect(mergeAnnotations(dupes, [])).toHaveLength(1);
  });

  it('keeps saved annotations that are no longer in the scan (no data loss)', () => {
    const saved: DepositionAnnotation[] = [
      { copick_kind: 'meshes', copick_ref: 'gone:auto/9', object_name: 'gone', is_selected: true },
    ];
    const merged = mergeAnnotations(scanned, saved);
    expect(merged.find((a) => a.copick_ref === 'gone:auto/9')).toBeTruthy();
    expect(merged).toHaveLength(3);
  });
});
