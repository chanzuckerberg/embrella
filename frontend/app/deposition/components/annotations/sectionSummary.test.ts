import type { DepositionAnnotation } from '../../types';
import { detailsFilled, doiCount, flagsSet, linkCount, methodFilled } from './sectionSummary';

const a = (over: Partial<DepositionAnnotation> = {}): DepositionAnnotation => ({
  copick_kind: 'picks',
  copick_ref: 'x:u/1',
  ...over,
});

it('detailsFilled counts state + description', () => {
  expect(detailsFilled(a())).toBe(0);
  expect(detailsFilled(a({ object_state: 'apo', object_description: 'x' }))).toBe(2);
  expect(detailsFilled(a({ object_state: '   ' }))).toBe(0); // whitespace-only doesn't count
});

it('methodFilled counts method + software only (not method_type)', () => {
  expect(methodFilled(a({ method_type: 'manual' }))).toBe(0);
  expect(methodFilled(a({ annotation_method: 'TM', annotation_software: 'copick' }))).toBe(2);
});

it('linkCount and doiCount', () => {
  expect(linkCount(a())).toBe(0);
  expect(linkCount(a({ method_links: [{ link_type: 'website', link: 'https://a' }] }))).toBe(1);
  expect(doiCount(a({ annotation_publication: '10.1/a, 10.2/b ,' }))).toBe(2);
  expect(doiCount(a())).toBe(0);
});

it('flagsSet counts true booleans', () => {
  expect(flagsSet(a())).toBe(0);
  expect(flagsSet(a({ ground_truth_status: true, is_visualization_default: true }))).toBe(2);
});
