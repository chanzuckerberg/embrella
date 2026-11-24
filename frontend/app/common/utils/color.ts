const WHITE = '#FFFFFF';
const BLACK = '#000000';
const HEX_RADIX = 16;
const CHANNEL_MAX = 255;

// Below this luminance a color is near-black, so darker shades would vanish.
const DARK_LUMINANCE = 0.2;

// Rec. 709 luma weights.
const LUMA = { r: 0.2126, g: 0.7152, b: 0.0722 };

// "fdb000" or "#FDB000" → "#fdb000".
export const toHex = (color: string) => `#${color.replace('#', '').toLowerCase()}`;

const channels = (color: string) => {
  const value = parseInt(toHex(color).slice(1), HEX_RADIX);

  return { r: (value >> 16) & CHANNEL_MAX, g: (value >> 8) & CHANNEL_MAX, b: value & CHANNEL_MAX };
};

// Blend `color` toward `target` by `amount` (0 = color, 1 = target), e.g. mix('#ff0000', '#000000', 0.5) → '#800000'.
export const mix = (color: string, target: string, amount: number) => {
  const from = channels(color);
  const to = channels(target);
  const blend = (a: number, b: number) =>
    Math.round(a + (b - a) * amount)
      .toString(HEX_RADIX)
      .padStart(2, '0');

  return `#${blend(from.r, to.r)}${blend(from.g, to.g)}${blend(from.b, to.b)}`;
};

export const darken = (color: string, amount: number) => mix(color, BLACK, amount);

export const lighten = (color: string, amount: number) => mix(color, WHITE, amount);

export const isDark = (color: string) => {
  const { r, g, b } = channels(color);
  const luminance = (LUMA.r * r + LUMA.g * g + LUMA.b * b) / CHANNEL_MAX;

  return luminance < DARK_LUMINANCE;
};
