import { InventoryGrid, toTrashedGrid } from './trashed';

const row = (user: string | null, project: string | null): InventoryGrid => ({
  grid: { id: 7, name: 'WT_RPE (id=7)' },
  user: { name: user },
  project: { name: project },
});

describe('toTrashedGrid', () => {
  it('joins owner and project into the detail line', () => {
    expect(toTrashedGrid(row('User Name', 'Proj'))).toEqual({
      id: 7,
      name: 'WT_RPE (id=7)',
      detail: 'User Name · Proj',
    });
  });

  it('drops unknown parts', () => {
    expect(toTrashedGrid(row(null, 'Proj')).detail).toBe('Proj');
    expect(toTrashedGrid(row(null, null)).detail).toBe('');
  });
});
