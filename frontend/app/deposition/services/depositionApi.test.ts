import { annotatedTrustedCount } from './depositionApi';

describe('annotatedTrustedCount', () => {
  it('returns the count for a complete, filtered scan', () => {
    expect(annotatedTrustedCount({ count: 3, scanned: true, complete: true, filtered: true })).toBe(3);
  });

  it('trusts a complete scan when filtered is absent (default)', () => {
    expect(annotatedTrustedCount({ count: 3, scanned: true, complete: true })).toBe(3);
  });

  it('is undefined when the scan did not cover the whole project', () => {
    expect(annotatedTrustedCount({ count: 3, scanned: true, complete: false })).toBeUndefined();
  });

  it('is undefined when the count could not be intersected with the run', () => {
    expect(annotatedTrustedCount({ count: 3, scanned: true, complete: true, filtered: false })).toBeUndefined();
  });

  it('is undefined for missing data', () => {
    expect(annotatedTrustedCount(undefined)).toBeUndefined();
  });
});
