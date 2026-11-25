'use client';

/**
 * Picked locations: thin state over the pure updates in selection.ts.
 */

import { useState } from 'react';
import { addAll, removeAll, togglePick } from './selection';
import { Membership, PickedLocation, SelectMode } from './types';

export const useSelection = (mode: SelectMode, capacity: number, initial: PickedLocation[] = []) => {
  const [picks, setPicks] = useState<PickedLocation[]>(initial);

  const limit = mode === SelectMode.Multi ? capacity : 1;

  return {
    mode,
    picks,
    capacity: limit,
    room: limit - picks.length,
    isPicked: (key: string) => picks.some((p) => p.key === key),
    toggle: (pick: PickedLocation) => setPicks((cur) => togglePick(cur, pick, mode, limit)),
    setMany: (many: PickedLocation[], membership: Membership) =>
      setPicks((cur) => (membership === Membership.Add ? addAll(cur, many, limit) : removeAll(cur, many))),
    remove: (key: string) => setPicks((cur) => cur.filter((p) => p.key !== key)),
    clear: () => setPicks([]),
  };
};

export type Selection = ReturnType<typeof useSelection>;
