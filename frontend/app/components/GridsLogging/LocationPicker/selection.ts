/**
 * Pick list updates, as pure functions. A list in both modes, so multi-select needs no reshaping:
 *   Single: picking replaces (re-picking clears) → at most 1
 *   Multi:  picking toggles, ignored when full; whole boxes add all-or-nothing
 */

import { PickedLocation, SelectMode } from './types';

export const togglePick = (picks: PickedLocation[], pick: PickedLocation, mode: SelectMode, capacity: number) => {
  const picked = picks.some((p) => p.key === pick.key);

  if (mode === SelectMode.Single) return picked ? [] : [pick];
  if (picked) return picks.filter((p) => p.key !== pick.key);
  if (picks.length >= capacity) return picks;

  return [...picks, pick];
};

// Adds the not-yet-picked ones only if they all fit, so a box never lands half on the cassette.
export const addAll = (picks: PickedLocation[], more: PickedLocation[], capacity: number) => {
  const fresh = more.filter((m) => !picks.some((p) => p.key === m.key));
  if (picks.length + fresh.length > capacity) return picks;

  return [...picks, ...fresh];
};

export const removeAll = (picks: PickedLocation[], gone: PickedLocation[]) => {
  const keys = new Set(gone.map((g) => g.key));

  return picks.filter((p) => !keys.has(p.key));
};
