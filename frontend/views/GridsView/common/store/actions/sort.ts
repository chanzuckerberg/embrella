import { ColumnSort, SortingState } from "@tanstack/react-table";
import { Updater } from "@tanstack/table-core";
import { GridData, SortBy } from "@/common/types";

/**
 * Builds the next sorting state.
 * @param updaterOrValue - Updater or value to update the sorting state.
 * @param sortBy - API sorting state.
 * @returns sorting state.
 */
export function buildNextSortState(
  updaterOrValue: Updater<SortingState>,
  sortBy?: SortBy<GridData>,
): SortingState {
  if (typeof updaterOrValue === "function") {
    return updaterOrValue(getSortingState(sortBy));
  }
  return updaterOrValue;
}

/**
 * Builds the current sorting state from given API sorting state.
 * @param sortBy - API sorting state.
 * @returns sorting state.
 */
export function getSortingState(sortBy?: SortBy<GridData>): SortingState {
  const sortingState: SortingState = [];
  if (!sortBy) return sortingState;
  sortingState.push(mapSortingState(sortBy));
  return sortingState;
}

/**
 * Maps the API sorting state to the sorting state.
 * @param sortBy - API sorting state.
 * @returns sorting state.
 */
function mapSortingState(sortBy: SortBy<GridData>): ColumnSort {
  return {
    desc: !sortBy.asc,
    id: sortBy.sort,
  };
}
