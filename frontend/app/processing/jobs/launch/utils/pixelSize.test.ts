import { resolvedPixelSize } from './pixelSize';

// Same cases as TestPixelSizeDerivation in aretomo3/tests/test_aretomo3.py.
describe('resolvedPixelSize', () => {
  it('lands on the sensor pixel when McBin and EerSampling cancel', () => {
    expect(resolvedPixelSize(2.0, false, 2, 2)).toBe(2.0);
  });

  it('halves the frame pixel for super-resolution', () => {
    expect(resolvedPixelSize(2.0, true, 2, 2)).toBe(1.0);
  });

  it('follows McBin', () => {
    expect(resolvedPixelSize(2.0, false, 1, 2)).toBe(1.0);
  });

  it('follows EerSampling', () => {
    expect(resolvedPixelSize(2.0, false, 2, 1)).toBe(4.0);
  });

  it('accepts the strings a text field holds', () => {
    expect(resolvedPixelSize('1.6', false, '2', '1')).toBeCloseTo(3.2);
  });

  it('is null while any input is blank or non-positive', () => {
    expect(resolvedPixelSize('', false, 2, 2)).toBeNull();
    expect(resolvedPixelSize(2.0, false, 0, 2)).toBeNull();
    expect(resolvedPixelSize(2.0, false, 2, undefined)).toBeNull();
  });
});
