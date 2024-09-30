import { TableState } from "@tanstack/react-table";
import { GridData, SortBy } from "@/common/types";
import { getSortingState } from "@/views/GridsView/common/store/actions/sort";

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
 * @param sortBy - API sorting state.
 * @returns table state.
 */
export function getTableState({
  sortBy,
}: {
  sortBy?: SortBy<GridData>;
}): Partial<TableState> {
  return {
    sorting: getSortingState(sortBy),
  };
}
