import {
  SEARCH_PARAM_NAME,
  SearchParam,
  SearchParamValue,
} from "@/common/types";
import { ColumnSort } from "@tanstack/react-table";
import { SORT_CATEGORY_VALUE } from "@/views/GridsView/hooks/useFetchGrids/constants";
import { State } from "@/views/GridsView/common/store/types";

/**
 * Returns filter list related search param "q" from the given state.
 * @param state - State.
 * @returns filter list related search param "q".
 */
export function buildFilterListSearchParam(state: State): SearchParam {
  return { [SEARCH_PARAM_NAME.QUERY]: getFilterSearchParamValue(state) };
}

/**
 * Returns grid list related search param "q" from the given state.
 * @param state - State.
 * @returns grid list related search param "q".
 */
export function buildGridListSearchParam(state: State): SearchParam {
  const values: SearchParamValue[] = [];
  // Add filter search param values.
  values.push(...getFilterSearchParamValue(state));
  // Add pagination search param values.
  values.push(...getPaginationSearchParamValue(state));
  // Add sort search param values.
  values.push(...getSortSearchParamValue(state));
  return { [SEARCH_PARAM_NAME.QUERY]: values };
}

/**
 * Returns the filter related search param values for the given filter state.
 * @param state - State.
 * @returns filter search param value.
 */
export function getFilterSearchParamValue(state: State): SearchParamValue[] {
  return Object.entries(state.filterState).map(([category, value]) => {
    return {
      category,
      value,
    };
  });
}

/**
 * Returns pagination related search param values for the given pagination state.
 * "pageSize" is configured in the BE, and therefore not included in the search params.
 * @param state - State.
 * @returns search params "page".
 */
export function getPaginationSearchParamValue(
  state: State,
): SearchParamValue[] {
  const {
    paginationState: { pageIndex },
  } = state;
  return [{ category: "page", value: [pageIndex].map(mapPageValue) }];
}

/**
 * Returns sort related search param values for the given sort state.
 * @param state - State.
 * @returns search params "sort" and "asc".
 */
export function getSortSearchParamValue(state: State): SearchParamValue[] {
  const { sortState } = state;
  return [
    { category: "asc", value: sortState.map(mapSortDirectionValue) },
    { category: "sort", value: sortState.map(mapSortValue) },
  ];
}

/**
 * Returns the page related search param values for the given pagination state.
 * @param pageIndex - Page index.
 * @returns page value.
 */
function mapPageValue(pageIndex: number): string {
  return String(pageIndex + 1);
}

/**
 * Maps the sort direction value for the given sort state.
 * @param columnSort - Column sort (from sort state).
 * @returns sort direction value.
 */
function mapSortDirectionValue(columnSort: ColumnSort): boolean {
  return !columnSort.desc;
}

/**
 * Maps the sort value for the given sort state, where sort id is mapped to expected sort value e.g. "updatedAt" column is mapped to "modifiedOn" value.
 * @param columnSort - Column sort (from sort state).
 * @returns sort column value.
 */
function mapSortValue(columnSort: ColumnSort): string {
  return SORT_CATEGORY_VALUE[columnSort.id] || columnSort.id;
}
