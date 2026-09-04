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
  it('maps picks/segmentations/meshes into copick_kind + copick_ref', () => {
    const out = normalizeScan({
      picks: [{ run_name: 'run001', object_name: 'VLP', user_id: 'relion', session_id: '2', count: 12345 }],
      segmentations: [{ run_name: 'run001', name: 'membrane', user_id: 'auto', session_id: '1' }],
      meshes: [{ run_name: 'run002', object_name: 'VLP_shells', user_id: 'auto', session_id: '1' }],
    });
    expect(out).toEqual([
      { copick_kind: 'picks', copick_ref: 'VLP:relion/2', object_name: 'VLP', run_name: 'run001', count: 12345 },
      { copick_kind: 'segmentations', copick_ref: 'membrane:auto/1', object_name: 'membrane', run_name: 'run001' },
      { copick_kind: 'meshes', copick_ref: 'VLP_shells:auto/1', object_name: 'VLP_shells', run_name: 'run002' },
    ]);
  });

  it('is safe on empty/partial input', () => {
    expect(normalizeScan({})).toEqual([]);
    expect(normalizeScan({ picks: [] })).toEqual([]);
  });
});

describe('mergeAnnotations', () => {
  const scanned: ScannedAnnotation[] = [
    { copick_kind: 'picks', copick_ref: 'VLP:relion/2', object_name: 'VLP', run_name: 'run001' },
    { copick_kind: 'picks', copick_ref: 'GroEL:upload/1', object_name: 'GroEL', run_name: 'run002' },
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
      { copick_kind: 'picks', copick_ref: 'VLP:relion/2', object_name: 'VLP', run_name: 'run001' },
      { copick_kind: 'picks', copick_ref: 'VLP:relion/2', object_name: 'VLP', run_name: 'run002' },
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
