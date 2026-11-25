import { Cane } from '@app/common/hooks/useGridLogging/list/useCaneList';
import { PuckList } from '@app/common/types/gridLogging';
import { FilterContext, filterPucks, NO_DEWAR, PuckFilter, smartOwner } from './puckFilters';
import { Owner, PickTarget } from './types';

const ME = 1;
const OTHER = 2;

const cane = (id: number, name: string, dewar: number | null): Cane =>
  ({ id, name, dewar, dewar_name: null }) as unknown as Cane;

const puck = (id: number, over: Partial<PuckList> = {}): PuckList =>
  ({
    id,
    name: `${id}`,
    user: OTHER,
    cane: 10,
    position_in_cane: 1,
    grid_box_count: 2,
    max_boxes: 12,
    ...over,
  }) as PuckList;

const CANES = [cane(10, '1', 1), cane(20, '2', 1), cane(30, 'dummy cane', null)];

const ctx = (over: Partial<FilterContext> = {}): FilterContext => ({
  userId: ME,
  target: PickTarget.Grid,
  myGridPucks: new Set(),
  caneById: new Map(CANES.map((c) => [c.id, c])),
  ...over,
});

const ALL: PuckFilter = { owner: Owner.All, ownerId: null, dewar: null, cane: null };
const ids = (pucks: PuckList[]) => pucks.map((p) => p.id);

describe('filterPucks', () => {
  it('orders by cane number, then position in cane, named canes last', () => {
    const pucks = [
      puck(1, { cane: 30 }),
      puck(2, { cane: 20, position_in_cane: 1 }),
      puck(3, { cane: 10, position_in_cane: 2 }),
      puck(4, { cane: 10, position_in_cane: 1 }),
    ];

    expect(ids(filterPucks(pucks, ALL, ctx()))).toEqual([4, 3, 2, 1]);
  });

  it('hides pucks with nothing to pick for the target', () => {
    const pucks = [puck(1, { grid_box_count: 0 }), puck(2, { grid_box_count: 12, max_boxes: 12 })];

    expect(ids(filterPucks(pucks, ALL, ctx({ target: PickTarget.Grid })))).toEqual([2]);
    expect(ids(filterPucks(pucks, ALL, ctx({ target: PickTarget.EmptySlot })))).toEqual([1]);
  });

  it.each([
    [Owner.Me, null, [1]],
    [Owner.MyGrids, null, [2]],
    [Owner.Person, OTHER, [2, 3]],
  ])('scopes by owner %s', (owner, ownerId, expected) => {
    const pucks = [puck(1, { user: ME }), puck(2), puck(3)];
    const filter = { ...ALL, owner, ownerId };

    expect(ids(filterPucks(pucks, filter, ctx({ myGridPucks: new Set([2]) })))).toEqual(expected);
  });

  it('filters by dewar and cane', () => {
    const pucks = [puck(1, { cane: 10 }), puck(2, { cane: 20 }), puck(3, { cane: 30 })];

    expect(ids(filterPucks(pucks, { ...ALL, dewar: NO_DEWAR }, ctx()))).toEqual([3]);
    expect(ids(filterPucks(pucks, { ...ALL, cane: 20 }, ctx()))).toEqual([2]);
  });
});

describe('smartOwner', () => {
  it('opens on my pucks when I own a useful one', () => {
    expect(smartOwner([puck(1, { user: ME })], ctx())).toBe(Owner.Me);
  });

  it('falls back to pucks with my grids, then all', () => {
    const pucks = [puck(1, { user: ME, grid_box_count: 0 }), puck(2)];

    expect(smartOwner(pucks, ctx({ myGridPucks: new Set([2]) }))).toBe(Owner.MyGrids);
    expect(smartOwner(pucks, ctx())).toBe(Owner.All);
  });

  it('stays on my pucks while loading', () => {
    expect(smartOwner([], ctx())).toBe(Owner.Me);
  });
});
