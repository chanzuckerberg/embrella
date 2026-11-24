/**
 * Shared look of drawn holders (grid box, puck): palette and slot styling.
 * Sizes are in a 200-unit drawing; scale them for larger viewBoxes.
 */

import { darken, isDark, lighten, toHex } from '@app/common/utils/color';

export const LABEL_COLOR = '#FFFFFF';

// How far each part shifts from the body color (0..1).
const SHADE = { ring: 0.35, line: 0.55, label: 0.6, slot: 0.6, occupied: 0.4, occupiedDark: 0.12, bore: 0.45 };

export const RING_WIDTH = 6;
export const LINE_WIDTH = 2.5;

// Hovered slot gets a bolder outline, so the click target is obvious.
export const HOVER_LINE_WIDTH = 4;

// Label outline width relative to font size: outlined digits.
export const LABEL_OUTLINE = 0.2;

// Highlighted slot: brightened with a dark glow; other occupied slots fade.
const SELECTED_GLOW = 6;

// Filter lengths are in viewBox units; pass `unit` for drawings larger than 200 units.
export const selectedFilter = (unit = 1) =>
  `brightness(1.3) drop-shadow(0 0 ${SELECTED_GLOW * unit}px rgba(0,0,0,0.8))`;
export const SELECTED_FILTER = selectedFilter();

// Grey that the filter brightens to near-white.
export const SELECTED_FILL = '#C0C0C0';
export const FADED_OPACITY = 0.2;

/**
 * Palette derived from the body color.
 * Dark bodies (e.g. black, navy) shift parts lighter so lines stay visible;
 * occupied slots stay near the body color to stand apart from light empty slots.
 *   fdb000 → ring #a47200, slots #fedf99, occupied #986a00
 *   0000c8 → ring #5959db, slots #9999e9, occupied #1f1fcf
 */
export const slotPalette = (color: string) => {
  const body = toHex(color);
  const dark = isDark(body);
  const contrast = (amount: number) => (dark ? lighten(body, amount) : darken(body, amount));

  return {
    body,
    ring: contrast(SHADE.ring),
    line: contrast(SHADE.line),
    label: dark ? body : darken(body, SHADE.label),
    slot: lighten(body, SHADE.slot),
    occupied: dark ? lighten(body, SHADE.occupiedDark) : darken(body, SHADE.occupied),
    bore: contrast(SHADE.bore),
  };
};
