/**
 * Location picker vocabulary.
 *
 *   PickTarget decides where drilling stops and what is clickable:
 *     Grid          puck → box → occupied position   (TEM session, screening)
 *     EmptySlot     puck → empty slot                (add / move grid box)
 *     EmptyPosition puck → box → empty position      (move grid)
 */

export enum PickTarget {
  Grid = 'grid',
  EmptySlot = 'empty-slot',
  EmptyPosition = 'empty-position',
}

// Single replaces the pick; Multi toggles up to a capacity (e.g. a 12-slot cassette).
export enum SelectMode {
  Single = 'single',
  Multi = 'multi',
}

export enum Owner {
  Me = 'me',
  MyGrids = 'my-grids', // pucks holding my grids, whoever owns the puck
  All = 'all',
  Person = 'person',
}

export enum Membership {
  Add = 'add',
  Remove = 'remove',
}

/**
 * One picked spot. `key` identifies it across navigation:
 *   "g1619" grid · "p79-s3" empty slot · "p79-s3-q2" empty position
 */
export interface PickedLocation {
  key: string;
  puckId: number;
  puckName: string;
  slot: number;
  gridBoxId?: number;
  boxName?: string;
  position?: number;
  gridId?: number;
  gridName?: string;
}

// Where the dialog opens; defaults to the owner gallery.
export interface PickerStart {
  puckId?: number;
  slot?: number;
}
