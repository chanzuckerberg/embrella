import { TableState } from "@app/common/components/TableStateProvider/TableStateProvider";
import { SearchParamValue } from "@app/common/types/search";

/**
 * Returns the filter related search param values for the given filter state.
 * @param state - State.
 * @returns filter search param value.
 */
export function getFilterSearchParamValues(
  state: TableState
): SearchParamValue[] {
  return Object.entries(state.filterState).map(([category, value]) => {
    return {
      category,
      value,
    };
  });
}
