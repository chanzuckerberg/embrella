/**
 * Grid inventory rows → trashed-grid hits.
 *   { grid: { id: 1619, name: "WT_RPE (id=1619)" }, user: { name: "User Name" }, project: { name: "P" } }
 *   → { id: 1619, name: "WT_RPE (id=1619)", detail: "User Name · P" }
 */

import { TrashedGrid } from './types';

export interface InventoryGrid {
  grid: { id: number; name: string };
  user: { name: string | null } | null;
  project: { name: string | null } | null;
}

export const toTrashedGrid = (row: InventoryGrid): TrashedGrid => ({
  id: row.grid.id,
  name: row.grid.name,
  detail: [row.user?.name, row.project?.name].filter(Boolean).join(' · '),
});
