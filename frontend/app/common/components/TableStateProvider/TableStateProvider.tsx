'use client';

import { createContext, Dispatch, ReactNode, useCallback, useMemo, useReducer } from 'react';
import { noop, PaginationState, SortingState, Updater } from '@tanstack/react-table';
import { EntityFilterCategories } from '@app/common/types/filter';
import { parseAsArrayOf, parseAsInteger, parseAsString, useQueryStates, type UseQueryStatesKeysMap } from 'nuqs';

// TODO: Determine if this can be deleted.
export const DEFAULT_PAGE_SIZE = 10;

type FilterValue = boolean | string | null;

type FilterState = Partial<{
  [K in EntityFilterCategories]: FilterValue | FilterValue[];
}>;

export const getInitialTableState = (sortState: SortingState = [], filterState: FilterState = {}): TableState => ({
  filterState,
  paginationState: {
    pageIndex: 0,
    pageSize: DEFAULT_PAGE_SIZE,
  },
  sortState,
});

interface TableStateProviderProps {
  children: ReactNode;
  filterCategories?: string[];
  initialSortState?: SortingState;
  initialFilterState?: FilterState;
  categoryMapping?: Record<string, string>;
}

export interface TableState {
  filterState: FilterState;
  paginationState: PaginationState;
  sortState: SortingState;
}

// #region Table state action types for reducer
export enum TableStateActionTypes {
  UpdateFilter = 'UPDATE_FILTER_ACTION',
  ClearAllFilters = 'CLEAR_ALL_FILTERS_ACTION',
  UpdatePagination = 'UPDATE_PAGINATION_ACTION',
  UpdateSort = 'UPDATE_SORT_ACTION',
}

interface CategoryFilter {
  category: EntityFilterCategories;
  value: FilterValue | FilterValue[];
}

export type UpdateFilterAction = {
  payload: {
    categoryFilter: CategoryFilter;
  };
  type: TableStateActionTypes.UpdateFilter;
};

export type UpdatePaginationAction = {
  payload: {
    pagination: PaginationState;
    updaterOrValue: Updater<PaginationState>;
  };
  type: TableStateActionTypes.UpdatePagination;
};

export type UpdateSortAction = {
  payload: {
    sortBy: SortingState;
    updaterOrValue: Updater<SortingState>;
  };
  type: TableStateActionTypes.UpdateSort;
};

export type ClearAllFiltersAction = {
  type: TableStateActionTypes.ClearAllFilters;
};

export type TableStateAction = UpdateFilterAction | UpdatePaginationAction | UpdateSortAction | ClearAllFiltersAction;
// #endregion Table state action types for reducer

export const tableStateReducer = (state: TableState, action: TableStateAction): TableState => {
  const { type } = action;
  switch (type) {
    case TableStateActionTypes.ClearAllFilters: {
      return {
        ...state,
        filterState: {},
        paginationState: {
          ...state.paginationState,
          pageIndex: 0,
        },
      };
    }
    case TableStateActionTypes.UpdateFilter: {
      const { payload } = action;
      const { category, value } = payload.categoryFilter;
      const valueSelected = Array.isArray(value) ? value.length > 0 : value !== null;
      const filterState = {
        ...state.filterState,
        [category]: value,
      };

      // Empty filter should be removed to prevent incorrect query to backend
      if (!valueSelected) {
        delete filterState[category];
      }

      return {
        ...state,
        filterState,
        paginationState: {
          ...state.paginationState,
          pageIndex: 0,
        },
      };
    }
    case TableStateActionTypes.UpdatePagination: {
      const { payload } = action;
      const { pagination, updaterOrValue } = payload;
      const paginationState = typeof updaterOrValue === 'function' ? updaterOrValue(pagination) : updaterOrValue;

      return {
        ...state,
        paginationState,
      };
    }
    case TableStateActionTypes.UpdateSort: {
      const { payload } = action;
      const { sortBy, updaterOrValue } = payload;
      const sortState = typeof updaterOrValue === 'function' ? updaterOrValue(sortBy) : updaterOrValue;
      return {
        ...state,
        sortState,
      };
    }
    default:
      return state;
  }
};

export const TableDispatchContext = createContext<Dispatch<TableStateAction>>(noop);
export const TableStateContext = createContext<TableState>(getInitialTableState());

/** Build nuqs parsers map from filter categories + sort/page params. */
function buildParsersMap(filterCategories: string[], categoryMapping: Record<string, string>): UseQueryStatesKeysMap {
  const parsers: UseQueryStatesKeysMap = {};

  for (const category of filterCategories) {
    const urlKey = categoryMapping[category] ?? category;
    parsers[urlKey] = parseAsArrayOf(parseAsString).withDefault([]);
  }

  parsers['sort'] = parseAsString;
  parsers['asc'] = parseAsString.withDefault('false');
  parsers['page'] = parseAsInteger.withDefault(1);

  return parsers;
}

/** Convert a URL string back to its original FilterValue type. */
function deserializeFilterValue(s: string): FilterValue {
  if (s === 'null') return null;
  if (s === 'true') return true;
  if (s === 'false') return false;
  return s;
}

/** Convert nuqs query state → TableState. */
function queryStateToTableState(
  queryState: Record<string, unknown>,
  filterCategories: string[],
  categoryMapping: Record<string, string>,
  initialSortState: SortingState
): TableState {
  const filterState: FilterState = {};

  for (const category of filterCategories) {
    const urlKey = categoryMapping[category] ?? category;
    const values = queryState[urlKey] as string[] | null;
    if (values && values.length > 0) {
      filterState[category as EntityFilterCategories] = values.map(deserializeFilterValue);
    }
  }

  const sortId = queryState['sort'] as string | null;
  const ascStr = queryState['asc'] as string;
  let sortState: SortingState;
  if (sortId) {
    sortState = [{ id: sortId, desc: ascStr !== 'true' }];
  } else {
    sortState = initialSortState;
  }

  const page = queryState['page'] as number;
  const pageIndex = Math.max(0, page - 1); // URL is 1-based, internal is 0-based

  return {
    filterState,
    paginationState: {
      pageIndex,
      pageSize: DEFAULT_PAGE_SIZE,
    },
    sortState,
  };
}

/** URL-synced provider: derives state from nuqs query params. */
function UrlSyncedProvider({
  children,
  filterCategories,
  initialSortState,
  categoryMapping,
}: Required<Omit<TableStateProviderProps, 'children' | 'initialFilterState'>> & { children: ReactNode }): JSX.Element {
  const parsersMap = useMemo(
    () => buildParsersMap(filterCategories, categoryMapping),
    [filterCategories, categoryMapping]
  );

  const nuqsOptions = useMemo(() => ({ history: 'replace' as const, shallow: true, clearOnDefault: true }), []);

  const [queryState, setQueryState] = useQueryStates(parsersMap, nuqsOptions);

  const tableState = useMemo(
    () => queryStateToTableState(queryState, filterCategories, categoryMapping, initialSortState),
    [queryState, filterCategories, categoryMapping, initialSortState]
  );

  const dispatch = useCallback(
    (action: TableStateAction) => {
      const { type } = action;
      switch (type) {
        case TableStateActionTypes.ClearAllFilters: {
          const updates: Record<string, null | number> = {};
          for (const category of filterCategories) {
            const urlKey = categoryMapping[category] ?? category;
            updates[urlKey] = null;
          }
          updates['page'] = 1;
          void setQueryState(updates);
          break;
        }
        case TableStateActionTypes.UpdateFilter: {
          const { category, value } = action.payload.categoryFilter;
          const urlKey = categoryMapping[category] ?? category;
          const valueSelected = Array.isArray(value) ? value.length > 0 : value !== null;

          const updates: Record<string, string[] | null | number> = {};
          if (valueSelected) {
            const values = Array.isArray(value) ? value : [value];
            updates[urlKey] = values.map((v) => String(v));
          } else {
            updates[urlKey] = null;
          }
          updates['page'] = 1;
          void setQueryState(updates);
          break;
        }
        case TableStateActionTypes.UpdatePagination: {
          const { pagination, updaterOrValue } = action.payload;
          const paginationState = typeof updaterOrValue === 'function' ? updaterOrValue(pagination) : updaterOrValue;
          void setQueryState({ page: paginationState.pageIndex + 1 });
          break;
        }
        case TableStateActionTypes.UpdateSort: {
          const { sortBy, updaterOrValue } = action.payload;
          const sortState = typeof updaterOrValue === 'function' ? updaterOrValue(sortBy) : updaterOrValue;
          if (sortState.length > 0) {
            void setQueryState({
              sort: sortState[0].id,
              asc: String(!sortState[0].desc),
            });
          } else {
            void setQueryState({ sort: null, asc: null });
          }
          break;
        }
      }
    },
    [filterCategories, categoryMapping, setQueryState]
  );

  return (
    <TableStateContext.Provider value={tableState}>
      <TableDispatchContext.Provider value={dispatch}>{children}</TableDispatchContext.Provider>
    </TableStateContext.Provider>
  );
}

/** Fallback provider: uses useReducer (no URL sync). */
function ReducerProvider({
  children,
  initialSortState,
  initialFilterState = {},
}: {
  children: ReactNode;
  initialSortState: SortingState;
  initialFilterState?: FilterState;
}): JSX.Element {
  const [state, dispatch] = useReducer(tableStateReducer, getInitialTableState(initialSortState, initialFilterState));

  return (
    <TableStateContext.Provider value={state}>
      <TableDispatchContext.Provider value={dispatch}>{children}</TableDispatchContext.Provider>
    </TableStateContext.Provider>
  );
}

export const TableStateProvider = ({
  children,
  filterCategories = [],
  initialSortState = [],
  initialFilterState = {},
  categoryMapping = {},
}: TableStateProviderProps): JSX.Element => {
  if (filterCategories.length > 0) {
    return (
      <UrlSyncedProvider
        filterCategories={filterCategories}
        initialSortState={initialSortState}
        categoryMapping={categoryMapping}
      >
        {children}
      </UrlSyncedProvider>
    );
  }

  return (
    <ReducerProvider initialSortState={initialSortState} initialFilterState={initialFilterState}>
      {children}
    </ReducerProvider>
  );
};
