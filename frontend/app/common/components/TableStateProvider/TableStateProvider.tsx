import { createContext, Dispatch, ReactNode, useReducer } from "react";
import { noop, PaginationState, SortingState, Updater } from "@tanstack/react-table";
import { FilterOption, ViewFilterCategory } from "@app/common/types/filter";
import { Pagination, SortBy } from "../../types/types";

export const DEFAULT_PAGE_SIZE = 10;

export const INITIAL_STATE: TableState = {
  filterState: {},
  paginationState: {
    pageIndex: 0,
    pageSize: DEFAULT_PAGE_SIZE,
  },
  sortState: [],
};

interface TableStateProviderProps {
  children: ReactNode;
}

type FilterValue = boolean | string | null;

type FilterState = Partial<{
  [K in ViewFilterCategory]: FilterValue[];
}>;

export interface TableState {
  filterState: FilterState;
  paginationState: PaginationState;
  sortState: SortingState;
}

// #region Table state actions for reducer
export enum TableStateActionTypes {
  UpdateFilter = "UPDATE_FILTER_ACTION",
  UpdatePagination = "UPDATE_PAGINATION_ACTION",
  UpdateSort = "UPDATE_SORT_ACTION",
}

interface CategoryFilter {
  category: ViewFilterCategory;
  value: FilterValue[];
}

interface FiltersList {
  filters: Record<ViewFilterCategory, FilterOption[]>;
}

export type UpdateFilterAction = {
  payload: {
    categoryFilter: CategoryFilter;
    filtersList?: FiltersList;
  };
  type: TableStateActionTypes.UpdateFilter;
};

export type UpdatePaginationAction = {
  payload: {
    pagination?: Pagination;
    updaterOrValue: Updater<PaginationState>;
  };
  type: TableStateActionTypes.UpdatePagination;
};

export type UpdateSortAction = {
  payload: {
    sortBy?: SortBy;
    updaterOrValue: Updater<SortingState>;
  };
  type: TableStateActionTypes.UpdateSort;
};

type TableStateAction =
  | UpdateFilterAction
  | UpdatePaginationAction
  | UpdateSortAction;
// #endregion Table state actions for reducer

export function tableStateReducer(state: TableState, action: TableStateAction): TableState {
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
    // TODO: move functions in frontend/views/GridsView/common/store/actions/index.ts here
    // case TableStateActionTypes.UpdatePagination: {
    //   return updatePaginationAction(state, payload);
    // }
    // case TableStateActionTypes.UpdateSort: {
    //   return updateSortAction(state, payload);
    // }
    default:
      return state;
  }
};

export const DispatchContext = createContext<Dispatch<TableStateAction>>(noop);
export const TableStateContext = createContext<TableState>(INITIAL_STATE);

export const TableStateProvider = ({ children }: TableStateProviderProps): JSX.Element => {
  const [state, dispatch] = useReducer(tableStateReducer, INITIAL_STATE);

  return (
    <TableStateContext.Provider value={state}>
      <DispatchContext.Provider value={dispatch}>
        {children}
      </DispatchContext.Provider>
    </TableStateContext.Provider>
  );
};
