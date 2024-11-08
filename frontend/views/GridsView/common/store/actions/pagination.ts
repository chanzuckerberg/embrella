import { PaginationState } from "@tanstack/react-table";
import { Updater } from "@tanstack/table-core";
import { Pagination } from "@/app/common/types/types";
import { DEFAULT_PAGE_SIZE } from "@/views/GridsView/common/store/constants";

//TODO: these functions can probably be moved to where they are called

/**
 * Builds the next pagination state.
 * @param updaterOrValue - Updater or value to update the pagination state.
 * @param pagination - API pagination state.
 * @returns pagination state.
 */
export function buildNextPaginationState(
  updaterOrValue: Updater<PaginationState>,
  pagination?: Pagination
): PaginationState {
  if (typeof updaterOrValue === "function") {
    return updaterOrValue(getPaginationState(pagination));
  }
  return updaterOrValue;
}

/**
 * Builds the current pagination state from given API pagination state.
 * @param pagination - API pagination state.
 * @returns pagination state.
 */
export function getPaginationState(pagination?: Pagination): PaginationState {
  if (!pagination)
    return {
      pageIndex: 0,
      pageSize: DEFAULT_PAGE_SIZE,
    };
  const { page, pageSize } = pagination;
  return { pageIndex: page - 1, pageSize };
}
