/**
 * Display text for picker levels, owners and picks.
 */

import { Cane } from '@app/common/hooks/useGridLogging/list/useCaneList';
import { PuckList, UserList } from '@app/common/types/gridLogging';
import { Owner, PickedLocation } from './types';

// Breadcrumb separator (single right angle quote). Escaped: it looks like ">".
export const CRUMB = '\u203A';

const UNKNOWN_USER = 'Unknown user';

const OWNER_LABELS: Record<Exclude<Owner, Owner.Person>, string> = {
  [Owner.Me]: 'My pucks',
  [Owner.MyGrids]: 'Pucks with my grids',
  [Owner.All]: 'All pucks',
};

// Real name, else username without email domain.
export const friendlyName = (user?: UserList) => {
  if (!user) return UNKNOWN_USER;

  const realName = `${user.first_name} ${user.last_name}`.trim();

  return realName || user.clean_username;
};

// "My pucks", "Pucks with my grids", "User's pucks".
export const ownerLabel = (owner: Owner, ownerId: number | null, users: UserList[]) => {
  if (owner !== Owner.Person) return OWNER_LABELS[owner];

  return `${friendlyName(users.find((u) => u.id === ownerId))}'s pucks`;
};

export const caneLabel = (cane?: Cane) => (cane ? `Cane ${cane.name}` : 'No cane');

export const boxesLabel = (puck: PuckList) => `${puck.grid_box_count} box${puck.grid_box_count === 1 ? '' : 'es'}`;

// Button / chip text: the grid's name, else its place, e.g. "49 · slot 1 · pos 4".
export const pickLabel = (pick: PickedLocation) => {
  if (pick.gridName) return pick.gridName;

  const position = pick.position === undefined ? '' : ` · pos ${pick.position}`;

  return `${pick.puckName} · slot ${pick.slot}${position}`;
};
