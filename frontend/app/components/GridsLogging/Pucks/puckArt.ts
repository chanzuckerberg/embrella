/**
 * Puck geometry
 */

import type { Point } from '../GridBox/gridBoxLayout';

// Traced body outline.
export const OUTLINE_PATH =
  'M432 68h47l28 3 27 5 26 7 20 7 23 10 23 12 13 9 4 5 5 13 8 33 5 26 5 14 6 8 10 6 13 3 18 3 10 6 6 10 5 18 9 41 3 16 4 17 5 23 6 12 9 9 8 4 4 1h32l10 5 7 8 3 7 2 13v17l-2 29-4 26-6 26-9 29-10 25-8 16-9 17-12 19-12 17-11 14-12 14-15 16-10 9-14 11-12 11-1 1-2 12-8 16-11 12-9 6-8 4-16 3-15-1-13-4-16-9-8-4-3-1h-20l-13 4-10 5-10 8-2 4v13l4 8 8 5 11 4 3 5v8l-5 5-10 3-8 1h-38l-15-4-4-4-1-3-1-33-3-8-8-4-9 1-5 2-3 9v25l-2 11-5 5-10 3-8 1h-29l-15-2-9-3-5-6v-8l5-5 13-4 7-6 3-7v-9l-4-8-10-7-16-7-10-3h-12l-11 4-18 10-10 4-5 1h-22l-13-4-11-7-7-6-9-13-5-13-2-11-12-9-13-11-13-12-14-14-9-11-8-9-13-18-10-15-11-19-11-21-10-24-10-30-7-30-4-28-1-13v-35l3-14 5-7 9-6 5-2h32l10-4 8-7 6-9 7-29 20-91 6-10 8-6 8-3 22-2 12-6 7-7 5-12 7-29 7-31 6-18 4-5 20-12 24-12 23-9 22-7 25-6 25-4z';

// Outline footprint: box around the traced body, its center, and stroke room.
export const OUTLINE_CENTER: Point = { x: 455, y: 447 };
export const OUTLINE_EXTENT = 801;

// The outline grows around this point, leaving room between rim and slots.
export const OUTLINE_PIVOT: Point = { x: 455, y: 430 };

export const SLOT_RADIUS = 67;

// Slot centers on an even hex grid fitted to the traced slots: rows of 2-3-4-3.
const SLOT_ROWS = [2, 3, 4, 3];
const SLOT_PITCH: Point = { x: 186.5, y: 153 };
const FIRST_ROW_Y = 184;

export const SLOT_CENTERS: Record<number, Point> = Object.fromEntries(
  SLOT_ROWS.flatMap((count, row) =>
    Array.from({ length: count }, (_, i) => ({
      x: OUTLINE_PIVOT.x + (i - (count - 1) / 2) * SLOT_PITCH.x,
      y: FIRST_ROW_Y + row * SLOT_PITCH.y,
    }))
  ).map((center, i) => [i + 1, center])
);
