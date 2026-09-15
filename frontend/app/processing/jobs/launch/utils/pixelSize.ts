/**
 * Pixel size of the motion-corrected tilt series, the one -AtBin is relative to.
 * Mirrors AreTomo3Processor._calculate_auto_binning:
 *
 *   sensor_px ──(÷2 if super_res)──▶ frame_px ──(× McBin ÷ EerSampling)──▶ mc_px
 */

export const SUPER_RES_FACTOR = 2;
// Same precision as the backend's rounded -AtBin factors
export const PIXEL_SIZE_DECIMALS = 3;

const asPositive = (value: unknown): number | null => {
  const n = typeof value === 'number' ? value : parseFloat(String(value));
  return Number.isFinite(n) && n > 0 ? n : null;
};

export function resolvedPixelSize(
  sensorPixelSize: unknown,
  superResolution: boolean,
  mcBin: unknown,
  eerSampling: unknown
): number | null {
  const sensor = asPositive(sensorPixelSize);
  const bin = asPositive(mcBin);
  const sampling = asPositive(eerSampling);
  if (sensor === null || bin === null || sampling === null) return null;

  const frame = superResolution ? sensor / SUPER_RES_FACTOR : sensor;
  return (frame * bin) / sampling;
}
