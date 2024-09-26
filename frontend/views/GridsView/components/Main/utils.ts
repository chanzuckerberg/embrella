import { SEARCH_PARAM_NAME, SearchParam } from "@/common/types";
import { CategoryFilter, FilterState } from "@/components/Filter/common/types";

/**
 * Returns search param "q" for the given filter state.
 * @param filterState - Filter state.
 * @returns search param "q".
 */
export function buildFilterSearchParam<FilterCategory extends string>(
  filterState: FilterState<FilterCategory>,
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
 * @returns grid or filters list search param.
 */
export function buildSearchParam({
  qParam,
}: {
  ascParam?: SearchParam;
  pageParam?: SearchParam;
  pageSizeParam?: SearchParam;
  qParam: SearchParam;
  sortParam?: SearchParam;
}): SearchParam {
  const searchParam: SearchParam = {};
  if (Object.hasOwn(qParam, SEARCH_PARAM_NAME.FILTER)) {
    Object.assign(searchParam, qParam);
  }
  return searchParam;
}

/**
 * Returns the filter search param value for the given filter state.
 * @param filterState - Filter state.
 * @returns filter search param value.
 */
function getFilterSearchParamValue<FilterCategory extends string>(
  filterState: FilterState<FilterCategory>,
): CategoryFilter<FilterCategory>[] {
  return Object.entries(filterState).map(([category, value]) => {
    return {
      category,
      value,
    } as CategoryFilter<FilterCategory>;
  });
}

/**
 * Returns true if the given filter state is empty.
 * @param filterState - Filter state.
 * @returns true if the filter state is empty.
 */
function isFilterStateEmpty<FilterCategory extends string>(
  filterState: FilterState<FilterCategory>,
): boolean {
  return Object.keys(filterState).length === 0;
}
