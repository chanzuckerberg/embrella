import { formatBytes, humanize } from './format';

describe('formatBytes', () => {
  /**
   * These expectations are the output of `format_bytes` in
   * umbrella/processes/models.py for the same inputs. The storage explorer
   * renders server-formatted sizes and client-formatted sizes in adjacent rows,
   * so a divergence here shows up as the tiers appearing to disagree.
   */
  it.each([
    [0, '0.00 B'],
    [1, '1.00 B'],
    [1023, '1023.00 B'],
    [1024, '1.00 KB'],
    [1536, '1.50 KB'],
    [1024 ** 2, '1.00 MB'],
    [1024 ** 3, '1.00 GB'],
    [1024 ** 4, '1.00 TB'],
    [1024 ** 5, '1.00 PB'],
    // Past PB it keeps scaling the number rather than inventing a unit.
    [1024 ** 6, '1024.00 PB'],
    // Survey 6's real total.
    [375494235672290, '341.51 TB'],
  ])('formats %p as %p', (input, expected) => {
    expect(formatBytes(input)).toBe(expected);
  });

  it('treats null and undefined as zero', () => {
    expect(formatBytes(null)).toBe('0.00 B');
    expect(formatBytes(undefined)).toBe('0.00 B');
  });
});

describe('humanize', () => {
  it.each([
    ['camelCase', 'Camel Case'],
    ['sessionDate', 'Session Date'],
    ['name', 'Name'],
  ])('turns %p into %p', (input, expected) => {
    expect(humanize(input)).toBe(expected);
  });
});
