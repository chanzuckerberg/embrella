import type { DepositionAnnotation } from '../../types';
import {
  annotationNeedsMetadata,
  mergeAnnotations,
  mergeServerIds,
  normalizeScan,
  staleAnnotationIds,
  stripIncompleteLinks,
  type ScannedAnnotation,
} from './scan';

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
      picks: [
        { copick_ref: 'VLP:relion/2', object_name: 'VLP', object_id: 'GO:0170047', run_count: 3, total_count: 12345 },
      ],
      segmentations: [{ copick_ref: 'membrane:auto/1', object_name: 'membrane', run_count: 1, total_count: 0 }],
      meshes: [{ copick_ref: 'VLP_shells:auto/1', object_name: 'VLP_shells', run_count: 1, total_count: 0 }],
    });
    expect(out).toEqual([
      { copick_kind: 'picks', copick_ref: 'VLP:relion/2', object_name: 'VLP', object_id: 'GO:0170047', count: 12345 },
      { copick_kind: 'segmentations', copick_ref: 'membrane:auto/1', object_name: 'membrane', object_id: '', count: 0 },
      { copick_kind: 'meshes', copick_ref: 'VLP_shells:auto/1', object_name: 'VLP_shells', object_id: '', count: 0 },
    ]);
  });

  it('is safe on empty/partial input', () => {
    expect(normalizeScan({})).toEqual([]);
    expect(normalizeScan({ picks: [] })).toEqual([]);
  });
});

describe('mergeAnnotations', () => {
  const scanned: ScannedAnnotation[] = [
    { copick_kind: 'picks', copick_ref: 'VLP:relion/2', object_name: 'VLP', object_id: 'GO:0170047' },
    { copick_kind: 'picks', copick_ref: 'GroEL:upload/1', object_name: 'GroEL', object_id: '' },
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

  it('seeds object_id from the scan onto a fresh candidate', () => {
    const [vlp] = mergeAnnotations(scanned, []);
    expect(vlp.object_id).toBe('GO:0170047');
  });

  it('keeps a user-entered object_id over the scanned one', () => {
    const saved: DepositionAnnotation[] = [
      { copick_kind: 'picks', copick_ref: 'VLP:relion/2', object_name: 'VLP', object_id: 'UniProtKB:P0A6G7' },
    ];
    const vlp = mergeAnnotations(scanned, saved).find((a) => a.copick_ref === 'VLP:relion/2')!;
    expect(vlp.object_id).toBe('UniProtKB:P0A6G7');
  });

  it('returns the same saved reference when the scan adds nothing new (no autosave churn)', () => {
    const saved: DepositionAnnotation[] = [
      {
        copick_kind: 'picks',
        copick_ref: 'VLP:relion/2',
        object_name: 'VLP',
        object_id: 'GO:0170047',
        is_selected: true,
      },
      { copick_kind: 'picks', copick_ref: 'GroEL:upload/1', object_name: 'GroEL', object_id: '', is_selected: false },
    ];
    // Every scanned identity is already present with its values → no change → same ref back.
    expect(mergeAnnotations(scanned, saved)).toBe(saved);
  });

  it('dedupes the same (kind, ref) appearing across multiple runs', () => {
    const dupes: ScannedAnnotation[] = [
      { copick_kind: 'picks', copick_ref: 'VLP:relion/2', object_name: 'VLP', object_id: '' },
      { copick_kind: 'picks', copick_ref: 'VLP:relion/2', object_name: 'VLP', object_id: '' },
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

describe('mergeServerIds', () => {
  const local = (over: Partial<DepositionAnnotation> = {}): DepositionAnnotation => ({
    copick_kind: 'picks',
    copick_ref: 'VLP:relion/2',
    ...over,
  });

  it('copies annotation + link ids from the saved response onto matching local rows', () => {
    const before = [local({ method_links: [{ link_type: 'website', link: 'https://a.org' }] })];
    const saved = [local({ id: 7, method_links: [{ id: 42, link_type: 'website', link: 'https://a.org' }] })];
    const out = mergeServerIds(before, saved);
    expect(out[0].id).toBe(7);
    expect(out[0].method_links![0].id).toBe(42);
  });

  it('returns the same array reference when nothing changed (no autosave re-trigger)', () => {
    const before = [local({ id: 7, method_links: [{ id: 42, link_type: 'website', link: 'https://a.org' }] })];
    const saved = [local({ id: 7, method_links: [{ id: 42, link_type: 'website', link: 'https://a.org' }] })];
    expect(mergeServerIds(before, saved)).toBe(before);
  });

  it('does not clobber a link the user edited mid-save (no url match → stays id-less)', () => {
    const before = [local({ method_links: [{ link_type: 'website', link: 'https://EDITED.org' }] })];
    const saved = [local({ id: 7, method_links: [{ id: 42, link_type: 'website', link: 'https://a.org' }] })];
    const out = mergeServerIds(before, saved);
    expect(out[0].id).toBe(7); // annotation id still merges (stable kind/ref)
    expect(out[0].method_links![0].id).toBeUndefined(); // edited link keeps its typed value, no stale id
    expect(out[0].method_links![0].link).toBe('https://EDITED.org');
  });

  it('leaves unselected/unmatched local rows untouched', () => {
    const before = [local({ copick_ref: 'other:auto/1' })];
    expect(mergeServerIds(before, [])).toBe(before);
  });
});

describe('stripIncompleteLinks', () => {
  const ann = (links?: DepositionAnnotation['method_links']): DepositionAnnotation => ({
    copick_kind: 'picks',
    copick_ref: 'x:u/1',
    method_links: links,
  });

  it('drops links with a blank url so autosave cannot 400', () => {
    const out = stripIncompleteLinks(
      ann([
        { link_type: 'source_code', link: 'https://github.com/x/y' },
        { link_type: 'website', link: '' },
        { link_type: 'documentation', link: '   ' },
      ])
    );
    expect(out.method_links).toEqual([{ link_type: 'source_code', link: 'https://github.com/x/y' }]);
  });

  it('returns the same object when every link has a url (no needless copy)', () => {
    const a = ann([{ link_type: 'website', link: 'https://a.org' }]);
    expect(stripIncompleteLinks(a)).toBe(a);
  });

  it('is a no-op when there are no links', () => {
    const a = ann();
    expect(stripIncompleteLinks(a)).toBe(a);
  });
});

describe('staleAnnotationIds', () => {
  const row = (ref: string): DepositionAnnotation => ({ copick_kind: 'picks', copick_ref: ref });
  const scanned = (ref: string): ScannedAnnotation => ({
    copick_kind: 'picks',
    copick_ref: ref,
    object_name: '',
    object_id: '',
  });

  it('flags saved rows the completed scan no longer returns', () => {
    const list = [row('VLP:relion/2'), row('gone:auto/9')];
    const stale = staleAnnotationIds(list, { scanned: true, annotations: [scanned('VLP:relion/2')] });
    expect([...stale]).toEqual(['picks::gone:auto/9']);
  });

  it('flags nothing while the scan is still pending (not authoritative)', () => {
    const list = [row('gone:auto/9')];
    expect(staleAnnotationIds(list, { scanned: false, annotations: [] }).size).toBe(0);
    expect(staleAnnotationIds(list, null).size).toBe(0);
  });

  it('flags nothing when every saved row is still scanned', () => {
    const list = [row('VLP:relion/2')];
    expect(staleAnnotationIds(list, { scanned: true, annotations: [scanned('VLP:relion/2')] }).size).toBe(0);
  });
});
