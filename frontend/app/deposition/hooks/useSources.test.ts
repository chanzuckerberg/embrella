import { annotatedRefetchInterval } from './useSources';

describe('annotatedRefetchInterval', () => {
  it('polls (5s) while a completed response is not yet scanned', () => {
    expect(annotatedRefetchInterval({ count: 0, scanned: false })).toBe(5000);
  });

  it('stops once the scan has completed', () => {
    expect(annotatedRefetchInterval({ count: 3, scanned: true })).toBe(false);
  });

  it('stops before the first response (no data yet)', () => {
    expect(annotatedRefetchInterval(undefined)).toBe(false);
  });

  it('stops on a terminal error even if the last data was unscanned', () => {
    expect(annotatedRefetchInterval({ count: 0, scanned: false }, true)).toBe(false);
  });
});
