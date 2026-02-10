import { calculateNextRunName } from './runNumbers';

describe('calculateNextRunName', () => {
  it('returns run001 for empty run numbers', () => {
    expect(calculateNextRunName([])).toBe('run001');
  });

  it('increments from a single existing run', () => {
    expect(calculateNextRunName(['001'])).toBe('run002');
  });

  it('increments from multiple sequential runs', () => {
    expect(calculateNextRunName(['001', '002', '003'])).toBe('run004');
  });

  it('finds the max even when runs are out of order', () => {
    expect(calculateNextRunName(['003', '001', '002'])).toBe('run004');
  });

  it('handles gaps in run numbers', () => {
    expect(calculateNextRunName(['001', '005'])).toBe('run006');
  });

  it('pads the result to 3 digits', () => {
    expect(calculateNextRunName(['001'])).toBe('run002');
    expect(calculateNextRunName(['009'])).toBe('run010');
    expect(calculateNextRunName(['099'])).toBe('run100');
  });

  it('handles non-numeric strings gracefully (falls back to 0)', () => {
    expect(calculateNextRunName(['abc'])).toBe('run001');
  });

  it('handles mixed valid and invalid entries', () => {
    expect(calculateNextRunName(['abc', '003', 'xyz'])).toBe('run004');
  });
});
