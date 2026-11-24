import { darken, isDark, lighten, mix, toHex } from './color';

describe('color', () => {
  it('normalizes hex', () => {
    expect(toHex('FDB000')).toBe('#fdb000');
    expect(toHex('#fdb000')).toBe('#fdb000');
  });

  it('mixes toward a target', () => {
    expect(mix('#ff0000', '#000000', 0.5)).toBe('#800000');
    expect(darken('FFFFFF', 1)).toBe('#000000');
    expect(lighten('000000', 1)).toBe('#ffffff');
  });

  it('detects dark colors', () => {
    expect(isDark('000000')).toBe(true);
    expect(isDark('CF1E01')).toBe(false);
    expect(isDark('fff500')).toBe(false);
    expect(isDark('FFFFFF')).toBe(false);
  });
});
