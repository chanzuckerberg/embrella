/**
 * Grid box layout and numbering.
 *
 * Slots sit in 2 straight columns × N/2 rows, notch at 12 o'clock.
 * Numbering decides which position number each slot shows:
 *
 *            ucw   uccw   z     col (8-box only)
 *   notch    4 1   1 4    1 2   1 5
 *            3 2   2 3    3 4   2 6
 *                               3 7
 *                               4 8
 */

import type { GridLoggingChoicesResponse } from '@app/common/types/gridLogging/config/choices';

export enum GridBoxNumbering {
  Ucw = 'ucw',
  Uccw = 'uccw',
  Z = 'z',
  Col = 'col',
}

export enum Column {
  Left = 'left',
  Right = 'right',
}

export interface Cell {
  column: Column;
  row: number;
}

export interface Point {
  x: number;
  y: number;
}

// Every slot of the box, row by row.
export const boxCells = (maxGrids: number): Cell[] =>
  Array.from({ length: maxGrids / 2 }, (_, row) => [
    { column: Column.Left, row },
    { column: Column.Right, row },
  ]).flat();

// Position number shown on a slot.
export const slotLabel = ({ column, row }: Cell, maxGrids: number, numbering: string): number => {
  const rows = maxGrids / 2;
  const isLeft = column === Column.Left;

  switch (numbering) {
    case GridBoxNumbering.Uccw:
      return isLeft ? row + 1 : maxGrids - row;
    case GridBoxNumbering.Z:
      return isLeft ? 2 * row + 1 : 2 * row + 2;
    case GridBoxNumbering.Col:
      return isLeft ? row + 1 : rows + row + 1;
    case GridBoxNumbering.Ucw:
    default:
      return isLeft ? maxGrids - row : row + 1;
  }
};

/**
 * Slot center: columns at ±gap.x, rows spaced gap.y apart, centered vertically.
 * `bow` pushes middle rows outward so columns follow the box's curve:
 *   (  )   bow 0 → straight columns, bow 6 → middle rows 6 units further out
 */
export const slotCenter = ({ column, row }: Cell, maxGrids: number, center: Point, gap: Point, bow = 0): Point => {
  const middleRow = (maxGrids / 2 - 1) / 2;
  const side = column === Column.Left ? -1 : 1;

  // -1 at the top row, 0 at the middle, 1 at the bottom row.
  const spread = middleRow === 0 ? 0 : (row - middleRow) / middleRow;
  const outward = bow * (1 - spread * spread);

  return {
    x: center.x + side * (gap.x + outward),
    y: center.y + (row - middleRow) * gap.y,
  };
};

/**
 * Numbering options a box size supports, e.g. 8 → [col, z].
 * `current` stays listed so legacy boxes (an 8-box stored as ucw) still show their value.
 */
export const numberingOptions = (
  choices: GridLoggingChoicesResponse | undefined,
  maxGrids: number,
  current?: string
) => {
  const allowed = choices?.grid_box_numbering_by_size?.[maxGrids] ?? [];

  return (choices?.grid_box_numbering ?? []).filter(({ value }) => allowed.includes(value) || value === current);
};

// Default numbering for a box size: the first supported style.
export const defaultNumbering = (choices: GridLoggingChoicesResponse | undefined, maxGrids: number) =>
  choices?.grid_box_numbering_by_size?.[maxGrids]?.[0] ?? GridBoxNumbering.Ucw;

export interface Rect {
  x: number;
  y: number;
  width: number;
  height: number;
}

/**
 * Click area of a slot: its half of the box, within its row band.
 * End rows stretch to the rim, so the whole box is clickable.
 *   ┌─────┬─────┐
 *   │  1  │  5  │  ← each cell owns everything nearest its oval
 *   ├─────┼─────┤
 */
export const slotHitArea = (
  { column, row }: Cell,
  maxGrids: number,
  center: Point,
  gap: Point,
  radius: number
): Rect => {
  const lastRow = maxGrids / 2 - 1;
  const rowY = slotCenter({ column, row }, maxGrids, center, gap).y;
  const top = row === 0 ? center.y - radius : rowY - gap.y / 2;
  const bottom = row === lastRow ? center.y + radius : rowY + gap.y / 2;
  const left = column === Column.Left ? center.x - radius : center.x;

  return { x: left, y: top, width: radius, height: bottom - top };
};
