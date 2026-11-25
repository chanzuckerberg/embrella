'use client';

/**
 * Box and grid name search via the Grid Inventory grid-box endpoint (`?q=[{category, value}]`).
 * Grid hits land on a position, box hits on a slot.
 */

import { useMemo } from 'react';
import { useFetchData } from '@hooks/useFetchData/useFetchData';
import { API } from '@app/common/constants/api';
import { useDebounced } from '@app/common/hooks/useDebounced';

const SEARCH_PAGE = 20;
const SEARCH_DEBOUNCE_MS = 300;
const SEARCH_MIN_CHARS = 2;

enum Category {
  Search = 'search',
  PageSize = 'pageSize',
}

interface InventoryBox {
  gridBox: { id: number; name: string };
  puckId: number;
  puckName: string;
  positionInPuck: number;
  grids: { id: number; name: string; position_in_box: number }[];
}

export enum HitKind {
  Grid = 'grid',
  Box = 'box',
}

export interface SearchHit {
  key: string;
  kind: HitKind;
  label: string;
  puckId: number;
  puckName: string;
  slot: number;
  gridBoxId: number;
  boxName: string;
  position?: number;
  gridId?: number;
}

export const useLocationSearch = (term: string) => {
  const debounced = useDebounced(term.trim(), SEARCH_DEBOUNCE_MS);
  const active = debounced.length >= SEARCH_MIN_CHARS;
  const params = useMemo(
    () => ({
      q: [
        { category: Category.Search, value: [debounced] },
        { category: Category.PageSize, value: [SEARCH_PAGE] },
      ],
    }),
    [debounced]
  );
  const { data } = useFetchData<{ result: InventoryBox[] }>(API.GRID_BOXES, params, active);

  return useMemo(() => {
    if (!active) return [];

    const needle = debounced.toLowerCase();
    const hits: SearchHit[] = [];
    for (const box of data?.result ?? []) {
      const at = {
        puckId: box.puckId,
        puckName: box.puckName,
        slot: box.positionInPuck,
        gridBoxId: box.gridBox.id,
        boxName: box.gridBox.name,
      };

      if (box.gridBox.name.toLowerCase().includes(needle)) {
        hits.push({ key: `b${box.gridBox.id}`, kind: HitKind.Box, label: box.gridBox.name, ...at });
      }

      for (const grid of box.grids) {
        if (!grid.name.toLowerCase().includes(needle)) continue;

        hits.push({
          key: `g${grid.id}`,
          kind: HitKind.Grid,
          label: grid.name,
          ...at,
          position: grid.position_in_box,
          gridId: grid.id,
        });
      }
    }

    return hits;
  }, [data, debounced, active]);
};
