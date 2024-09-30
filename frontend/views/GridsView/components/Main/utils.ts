import {
  GridFilterCategory,
  SEARCH_PARAM_NAME,
  SearchParam,
} from "@/common/types";
import { CategoryFilter, FilterState } from "@/components/Filter/common/types";
import { SortingState } from "@tanstack/react-table";

/**
 * Returns search param "q" for the given filter state.
 * @param filterState - Filter state.
 * @returns search param "q".
 */
export function buildFilterSearchParam(
  filterState: FilterState<GridFilterCategory>,
): SearchParam {
  const searchParam: SearchParam = {};
  if (isFilterStateEmpty(filterState)) return searchParam;
  searchParam[SEARCH_PARAM_NAME.FILTER] =
    getFilterSearchParamValue(filterState);
  return searchParam;
}

/**
 * Returns grid or filters list search param for the given params.
 * @param qParam - Search param "q".
 * @param sortingParam - Search param "sort" and "asc".
 * @returns grid or filters list search param.
 */
export function buildSearchParam({
  qParam,
  sortingParam,
}: {
  pageParam?: SearchParam;
  pageSizeParam?: SearchParam;
  qParam: SearchParam;
  sortingParam?: SearchParam;
}): SearchParam {
  const searchParam: SearchParam = {};
  if (Object.hasOwn(qParam, SEARCH_PARAM_NAME.FILTER)) {
    Object.assign(searchParam, qParam);
  }
  if (sortingParam) {
    Object.assign(searchParam, sortingParam);
  }
  return searchParam;
}

/**
 * Returns search param "sort" and "asc" for the given sort state.
 * @param sortingState - Sorting state.
 * @returns search params "sort" and "asc".
 */
export function buildSortingSearchParam(
  sortingState: SortingState,
): SearchParam {
  const searchParam: SearchParam = {};
  // GridList currently configured for single sort only.
  searchParam[SEARCH_PARAM_NAME.SORT_COLUMN_NAME] = sortingState[0].id;
  searchParam[SEARCH_PARAM_NAME.SORT_DIRECTION] = !sortingState[0].desc;
  return searchParam;
}

/**
 * Returns the filter search param value for the given filter state.
 * @param filterState - Filter state.
 * @returns filter search param value.
 */
function getFilterSearchParamValue(
  filterState: FilterState<GridFilterCategory>,
): CategoryFilter<GridFilterCategory>[] {
  return Object.entries(filterState).map(([category, value]) => {
    return {
      category,
      value,
    } as CategoryFilter<GridFilterCategory>;
  });
}

/**
 * Returns true if the given filter state is empty.
 * @param filterState - Filter state.
 * @returns true if the filter state is empty.
 */
function isFilterStateEmpty(
  filterState: FilterState<GridFilterCategory>,
): boolean {
  return Object.keys(filterState).length === 0;
}
