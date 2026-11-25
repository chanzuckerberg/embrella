'use client';

/**
 * Trashed grids by the Grid Inventory search (`?q=[{category, value}]`, status Trashed):
 * same matching as the inventory page (name, project, owner, sample, label, id).
 * Runs only while the caller accepts trashed grids and the term is long enough.
 */

import { useMemo } from 'react';
import { useFetchData } from '@hooks/useFetchData/useFetchData';
import { API } from '@app/common/constants/api';
import { useDebounced } from '@app/common/hooks/useDebounced';
import { InventoryGrid, toTrashedGrid } from './trashed';
import { TrashedGrid } from './types';
import { SEARCH_DEBOUNCE_MS, SEARCH_MIN_CHARS } from './useLocationSearch';

const TRASHED_PAGE = 20;
const TRASHED_STATUS = 'Trashed';
const NONE: TrashedGrid[] = [];

enum Category {
  Search = 'search',
  Status = 'status',
  PageSize = 'pageSize',
}

export const useTrashedSearch = (term: string, enabled: boolean): TrashedGrid[] => {
  const debounced = useDebounced(term.trim(), SEARCH_DEBOUNCE_MS);
  const active = enabled && debounced.length >= SEARCH_MIN_CHARS;
  const params = useMemo(
    () => ({
      q: [
        { category: Category.Search, value: [debounced] },
        { category: Category.Status, value: [TRASHED_STATUS] },
        { category: Category.PageSize, value: [TRASHED_PAGE] },
      ],
    }),
    [debounced]
  );
  const { data } = useFetchData<{ result: InventoryGrid[] }>(API.GRIDS, params, active);

  return useMemo(() => (active ? (data?.result ?? []).map(toTrashedGrid) : NONE), [active, data]);
};
