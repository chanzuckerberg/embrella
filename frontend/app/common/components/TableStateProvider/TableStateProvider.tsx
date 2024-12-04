import { createContext, Dispatch, ReactNode, useReducer } from "react";
import {
  noop,
  PaginationState,
  SortingState,
  Updater,
} from "@tanstack/react-table";
import { EntityFilterCategories } from "@app/common/types/filter";

export const DEFAULT_PAGE_SIZE = 10;

export const getInitialTableState = (
  sortState: SortingState = [],
): TableState => ({
  filterState: {},
  paginationState: {
    pageIndex: 0,
    pageSize: DEFAULT_PAGE_SIZE,
  },
  sortState,
});

interface TableStateProviderProps {
  children: ReactNode;
  initialSortState?: SortingState;
}

type FilterValue = boolean | string | null;

type FilterState = Partial<{
  [K in EntityFilterCategories]: FilterValue[];
}>;

export interface TableState {
  filterState: FilterState;
  paginationState: PaginationState;
  sortState: SortingState;
}

// #region Table state action types for reducer
export enum TableStateActionTypes {
  UpdateFilter = "UPDATE_FILTER_ACTION",
  UpdatePagination = "UPDATE_PAGINATION_ACTION",
  UpdateSort = "UPDATE_SORT_ACTION",
}

interface CategoryFilter {
  category: EntityFilterCategories;
  value: FilterValue[];
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

export type TableStateAction =
  | UpdateFilterAction
  | UpdatePaginationAction
  | UpdateSortAction;
// #endregion Table state action types for reducer

export const tableStateReducer = (
  state: TableState,
  action: TableStateAction,
): TableState => {
  const { payload, type } = action;
  switch (type) {
    case TableStateActionTypes.UpdateFilter: {
      const { category, value } = payload.categoryFilter;
      const valueSelected = value.length > 0;
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
      };
    }
    case TableStateActionTypes.UpdatePagination: {
      const { pagination, updaterOrValue } = payload;
      const paginationState =
        typeof updaterOrValue === "function"
          ? updaterOrValue(pagination)
          : updaterOrValue;

      return {
        ...state,
        paginationState,
      };
    }
    case TableStateActionTypes.UpdateSort: {
      const { sortBy, updaterOrValue } = payload;
      const sortState =
        typeof updaterOrValue === "function"
          ? updaterOrValue(sortBy)
          : updaterOrValue;
      return {
        ...state,
        sortState,
      };
    }
    default:
      return state;
  }
};

export const TableDispatchContext =
  createContext<Dispatch<TableStateAction>>(noop);
export const TableStateContext = createContext<TableState>(
  getInitialTableState(),
);

export const TableStateProvider = ({
  children,
  initialSortState,
}: TableStateProviderProps): JSX.Element => {
  const sortState = initialSortState || [];
  const [state, dispatch] = useReducer(
    tableStateReducer,
    getInitialTableState(sortState),
  );

  return (
    <TableStateContext.Provider value={state}>
      <TableDispatchContext.Provider value={dispatch}>
        {children}
      </TableDispatchContext.Provider>
    </TableStateContext.Provider>
  );
};
