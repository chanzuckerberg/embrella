import { createContext, Dispatch, ReactNode, useReducer } from "react";
import { noop, PaginationState, SortingState, Updater } from "@tanstack/react-table";
import { FiltersList, ViewFilterCategory } from "@app/common/types/filter";
import { Pagination, SortBy } from "../../types/types";
import { TOMOGRAM_COLUMN_DEFS, TOMOGRAM_COLUMN_IDS } from "@/app/components/TomogramsView/components/TomogramTable/columns";

export const DEFAULT_PAGE_SIZE = 10;

export const INITIAL_STATE: TableState = {
  filterState: {},
  paginationState: {
    pageIndex: 0,
    pageSize: DEFAULT_PAGE_SIZE,
  },
  sortState: [{ desc: true, id: TOMOGRAM_COLUMN_IDS.CREATED_AT as string }],
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

export const getReactTablePaginationState = (pagination: Pagination): PaginationState => (
  !pagination
  ? { pageIndex: 0, pageSize: DEFAULT_PAGE_SIZE }
  : {
      pageIndex: pagination.page - 1,
      pageSize: pagination.pageSize,
    }
)

export const getReactTableSortingState = (sortBy: SortBy): SortingState => (
  !sortBy
  ? []
  : [ { id: sortBy.sort, desc: !sortBy.asc } ]
);

const tableStateReducer = (state: TableState, action: TableStateAction): TableState => {
  const { payload, type } = action;
  switch (type) {
    case TableStateActionTypes.UpdateFilter:
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

      const nextState = {
        ...state,
        filterState,
      };
      return nextState;
    case TableStateActionTypes.UpdatePagination:
      const { pagination, updaterOrValue: paginationUpdaterOrValue} = payload;
      const paginationState = typeof paginationUpdaterOrValue === "function" ?
        paginationUpdaterOrValue(getReactTablePaginationState(pagination as Pagination)) :
        paginationUpdaterOrValue;
      return {
        ...state,
        paginationState,
      }
    case TableStateActionTypes.UpdateSort:
      const { sortBy, updaterOrValue: sortUpdaterOrValue} = payload;
      const sortState = typeof sortUpdaterOrValue === "function" ?
        sortUpdaterOrValue(getReactTableSortingState(sortBy as SortBy)) :
        sortUpdaterOrValue;

      return {
        ...state,
        sortState,
      }
    default:
      return state;
  }
};

export const TableDispatchContext = createContext<Dispatch<TableStateAction>>(noop);
export const TableStateContext = createContext<TableState>(INITIAL_STATE);

export const TableStateProvider = ({ children }: TableStateProviderProps): JSX.Element => {
  const [state, dispatch] = useReducer(tableStateReducer, INITIAL_STATE);

  return (
    <TableStateContext.Provider value={state}>
      <TableDispatchContext.Provider value={dispatch}>
        {children}
      </TableDispatchContext.Provider>
    </TableStateContext.Provider>
  );
};
