'use client';

/**
 * Picker navigation: filters narrow the puck list, the path opens a puck and then a box.
 *
 *   filters (dewar, cane, owner) ──▶ puck list
 *   path    (puck › slot)         ──▶ puck or box on screen
 */

import { useMemo, useState } from 'react';
import { useGridLoggingCaneList, useGridLoggingUserList } from '@app/common/hooks/useGridLogging';
import {
  useGridLoggingPucksByGridOwner,
  useGridLoggingPucksList,
} from '@app/common/hooks/useGridLogging/other/useGridLoggingPuckList';
import { friendlyName } from './labels';
import { byCane, dewarOf, filterPucks, FilterContext, NO_DEWAR, smartOwner } from './puckFilters';
import { Owner, PickerStart, PickTarget } from './types';

interface Nav {
  dewar: number | null;
  cane: number | null;
  owner: Owner;
  ownerId: number | null; // with Owner.Person
  ownerChosen: boolean; // user picked an owner; ends the smart default
  puckId: number | null;
  slot: number | null;
}

const startNav = (start?: PickerStart): Nav => ({
  dewar: null,
  cane: null,
  owner: Owner.Me,
  ownerId: null,
  ownerChosen: false,
  puckId: start?.puckId ?? null,
  slot: start?.slot ?? null,
});

const NO_DEWAR_LABEL = 'No dewar';

export const usePickerNav = (userId: number | null, target: PickTarget, start?: PickerStart) => {
  const [nav, setNav] = useState<Nav>(() => startNav(start));
  const { canes } = useGridLoggingCaneList();
  const { pucks: pucksData } = useGridLoggingPucksList();
  const { users: usersData } = useGridLoggingUserList();

  const smartPending = !nav.ownerChosen;
  const needsGridPucks = nav.owner === Owner.MyGrids || smartPending;
  const { pucks: gridPucksData } = useGridLoggingPucksByGridOwner(needsGridPucks ? (userId ?? undefined) : undefined);

  const users = useMemo(() => usersData?.users ?? [], [usersData]);
  const allPucks = useMemo(() => pucksData?.pucks ?? [], [pucksData]);
  const caneById = useMemo(() => new Map(canes.map((c) => [c.id, c])), [canes]);
  const myGridPucks = useMemo(() => new Set((gridPucksData?.pucks ?? []).map((p) => p.id)), [gridPucksData]);
  const userById = useMemo(() => new Map(users.map((u) => [u.id, u])), [users]);

  const ctx: FilterContext = useMemo(
    () => ({ userId, target, myGridPucks, caneById }),
    [userId, target, myGridPucks, caneById]
  );

  // Scope shown: the smart default until the user picks one.
  const owner = smartPending ? smartOwner(allPucks, ctx) : nav.owner;

  const pucks = useMemo(
    () => filterPucks(allPucks, { owner, ownerId: nav.ownerId, dewar: nav.dewar, cane: nav.cane }, ctx),
    [allPucks, owner, nav.ownerId, nav.dewar, nav.cane, ctx]
  );

  // Dewars by id with names from the cane list (no dewar endpoint); canes by number.
  const dewars = useMemo(() => {
    const names = new Map<number, string>();
    for (const c of canes) names.set(dewarOf(c), c.dewar_name ?? NO_DEWAR_LABEL);

    return [...names.entries()].sort(([a], [b]) => a - b).map(([id, name]) => ({ id, name }));
  }, [canes]);
  const canesInDewar = useMemo(
    () => canes.filter((c) => nav.dewar === null || dewarOf(c) === nav.dewar).sort(byCane),
    [canes, nav.dewar]
  );

  const puck = allPucks.find((p) => p.id === nav.puckId);
  const puckCane = puck ? caneById.get(puck.cane) : undefined;

  // Changing a filter clears the path below it.
  const clearPath = { puckId: null, slot: null };
  const actions = {
    setDewar: (dewar: number | null) => setNav((n) => ({ ...n, ...clearPath, dewar, cane: null })),
    setCane: (cane: number | null) =>
      setNav((n) => ({ ...n, ...clearPath, cane, dewar: cane === null ? n.dewar : dewarOf(caneById.get(cane)) })),
    setOwner: (next: Owner, ownerId: number | null = null) =>
      setNav((n) => ({ ...n, ...clearPath, owner: next, ownerId, ownerChosen: true })),
    jumpTo: (puckId: number, slot: number) => setNav((n) => ({ ...n, puckId, slot })),
    openPuck: (puckId: number | null) => setNav((n) => ({ ...n, ...clearPath, puckId })),
    openSlot: (slot: number | null) => setNav((n) => ({ ...n, slot })),
  };

  return {
    nav: { ...nav, owner },
    actions,
    target,
    users,
    nameOf: (id: number) => friendlyName(userById.get(id)),
    dewars,
    dewarName: (id: number | null) => dewars.find((d) => d.id === id)?.name ?? (id === NO_DEWAR ? NO_DEWAR_LABEL : ''),
    canesInDewar,
    caneById,
    allPucks,
    pucks,
    puck,
    puckCane,
    puckDewar: puck ? dewarOf(puckCane) : null,
  };
};

export type PickerNav = ReturnType<typeof usePickerNav>;
