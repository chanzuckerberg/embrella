import { boxCells, Column, GridBoxNumbering, slotCenter, slotHitArea, slotLabel } from './gridBoxLayout';

// Labels in reading order: one [left, right] pair per row, top to bottom.
const rowsOf = (maxGrids: number, numbering: GridBoxNumbering) => {
  const rows = Array.from({ length: maxGrids / 2 }, () => [0, 0]);

  for (const cell of boxCells(maxGrids)) {
    rows[cell.row][cell.column === Column.Left ? 0 : 1] = slotLabel(cell, maxGrids, numbering);
  }

  return rows;
};

describe('slotLabel', () => {
  it.each([
    [
      4,
      GridBoxNumbering.Ucw,
      [
        [4, 1],
        [3, 2],
      ],
    ],
    [
      4,
      GridBoxNumbering.Uccw,
      [
        [1, 4],
        [2, 3],
      ],
    ],
    [
      4,
      GridBoxNumbering.Z,
      [
        [1, 2],
        [3, 4],
      ],
    ],
    [
      8,
      GridBoxNumbering.Z,
      [
        [1, 2],
        [3, 4],
        [5, 6],
        [7, 8],
      ],
    ],
    [
      8,
      GridBoxNumbering.Col,
      [
        [1, 5],
        [2, 6],
        [3, 7],
        [4, 8],
      ],
    ],
  ])('%i-box %s', (maxGrids, numbering, expected) => {
    expect(rowsOf(maxGrids, numbering)).toEqual(expected);
  });
});

describe('slotCenter', () => {
  it('centers rows around the box center', () => {
    const center = { x: 100, y: 100 };
    const gap = { x: 30, y: 40 };

    expect(slotCenter({ column: Column.Left, row: 0 }, 4, center, gap)).toEqual({ x: 70, y: 80 });
    expect(slotCenter({ column: Column.Right, row: 1 }, 4, center, gap)).toEqual({ x: 130, y: 120 });
  });
});

describe('slotCenter bow', () => {
  it('pushes middle rows outward and keeps end rows in place', () => {
    const center = { x: 0, y: 0 };
    const gap = { x: 30, y: 40 };
    const x = (row: number) => slotCenter({ column: Column.Right, row }, 8, center, gap, 9).x;

    expect(x(0)).toBe(30);
    expect(x(1)).toBe(38);
    expect(x(2)).toBe(38);
    expect(x(3)).toBe(30);
  });
});

describe('slotHitArea', () => {
  const center = { x: 100, y: 100 };
  const gap = { x: 30, y: 40 };

  it('stretches end rows to the rim and splits inner rows halfway', () => {
    expect(slotHitArea({ column: Column.Left, row: 0 }, 8, center, gap, 90)).toEqual({
      x: 10,
      y: 10,
      width: 90,
      height: 50,
    });
    expect(slotHitArea({ column: Column.Right, row: 1 }, 8, center, gap, 90)).toEqual({
      x: 100,
      y: 60,
      width: 90,
      height: 40,
    });
  });
});
