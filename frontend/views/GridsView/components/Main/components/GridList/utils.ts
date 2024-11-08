import { TableState } from "@tanstack/react-table";
import { GridData, Pagination, SortBy } from "@/app/common/types/types";
import { getSortingState } from "@/views/GridsView/common/store/actions/sort";
import { getPaginationState } from "@/views/GridsView/common/store/actions/pagination";

/**
 * Returns grid row ID.
 * @param row - Grid row.
 * @returns grid row ID.
 */
export function getRowId(row: GridData): string {
  const {
    grid: { id },
  } = row;
  return id.toString();
}

/**
 * Returns state for the table.
 * @param pagination - API pagination state.
 * @param sortBy - API sorting state.
 * @returns table state.
 */
export function getTableState({
  pagination,
  sortBy,
}: {
  pagination?: Pagination;
  sortBy?: SortBy;
}): Partial<TableState> {
  return {
    pagination: getPaginationState(pagination),
    sorting: getSortingState(sortBy),
  };
}
