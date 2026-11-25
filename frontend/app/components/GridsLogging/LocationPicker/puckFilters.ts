/**
 * Which pucks the gallery lists, in what order, and the owner scope it opens on.
 *
 *   all pucks ─▶ useful for target ─▶ owner scope ─▶ dewar ─▶ cane ─▶ sort (cane number › position)
 */

import { Cane } from '@app/common/hooks/useGridLogging/list/useCaneList';
import { PuckList } from '@app/common/types/gridLogging';
import { Owner, PickTarget } from './types';

// Canes without a dewar group here.
export const NO_DEWAR = 0;

export const dewarOf = (cane?: Cane) => cane?.dewar ?? NO_DEWAR;

// Cane number from its name ("3" → 3); named canes ("dummy cane") sort last.
const caneNumber = (cane?: Cane) => {
  const n = Number.parseInt(cane?.name ?? '', 10);
  return Number.isNaN(n) ? Infinity : n;
};

// Cane number, then name for ties among named canes.
export const byCane = (a?: Cane, b?: Cane) =>
  caneNumber(a) - caneNumber(b) || (a?.name ?? '').localeCompare(b?.name ?? '');

// A puck is worth listing if it has something to pick: boxes for grids/positions, a free slot for boxes.
export const isUseful = (puck: PuckList, target: PickTarget) =>
  target === PickTarget.EmptySlot ? puck.grid_box_count < puck.max_boxes : puck.grid_box_count > 0;

export interface PuckFilter {
  owner: Owner;
  ownerId: number | null; // with Owner.Person
  dewar: number | null;
  cane: number | null;
}

export interface FilterContext {
  userId: number | null;
  target: PickTarget;
  myGridPucks: Set<number>;
  caneById: Map<number, Cane>;
}

const ownerMatch = (filter: PuckFilter, ctx: FilterContext): Record<Owner, (p: PuckList) => boolean> => ({
  [Owner.Me]: (p) => p.user === ctx.userId,
  [Owner.MyGrids]: (p) => ctx.myGridPucks.has(p.id),
  [Owner.All]: () => true,
  [Owner.Person]: (p) => p.user === filter.ownerId,
});

export const filterPucks = (pucks: PuckList[], filter: PuckFilter, ctx: FilterContext) =>
  pucks
    .filter((p) => isUseful(p, ctx.target))
    .filter(ownerMatch(filter, ctx)[filter.owner])
    .filter((p) => filter.dewar === null || dewarOf(ctx.caneById.get(p.cane)) === filter.dewar)
    .filter((p) => filter.cane === null || p.cane === filter.cane)
    .sort(
      (a, b) =>
        byCane(ctx.caneById.get(a.cane), ctx.caneById.get(b.cane)) ||
        (a.position_in_cane ?? 0) - (b.position_in_cane ?? 0)
    );

/**
 * Opening scope, so nobody lands on an empty list: my pucks → pucks with my grids → all.
 * "My pucks" while pucks are still loading, to avoid flashing another scope.
 */
export const smartOwner = (pucks: PuckList[], ctx: FilterContext) => {
  if (!pucks.length) return Owner.Me;
  if (pucks.some((p) => p.user === ctx.userId && isUseful(p, ctx.target))) return Owner.Me;
  if (pucks.some((p) => ctx.myGridPucks.has(p.id) && isUseful(p, ctx.target))) return Owner.MyGrids;

  return Owner.All;
};
