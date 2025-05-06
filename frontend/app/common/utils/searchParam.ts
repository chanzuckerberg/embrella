import { TableState } from '@app/common/components/TableStateProvider/TableStateProvider';
import { SearchParamValue } from '@app/common/types/search';
import { ColumnSort } from '@tanstack/react-table';

/**
 * Returns the filter related search param values for the given filter state.
 * @param state - State.
 * @returns filter search param value.
 */
export function getFilterSearchParamValues(state: TableState): SearchParamValue[] {
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
export const getPaginationSearchParamValues = (state: TableState): SearchParamValue[] => {
  const {
    paginationState: { pageIndex },
  } = state;

  const pageNumbersForIndexes = [pageIndex].map((pageIndex: number) => pageIndex + 1);

  return [
    {
      category: 'page',
      value: pageNumbersForIndexes,
    },
  ];
};

/**
 * Returns sort related search param values for the given sort state.
 * @param state - State.
 * @returns search params "sort" and "asc".
 */
export function getSortSearchParamValue(state: TableState): SearchParamValue[] {
  const { sortState } = state;
  return [
    {
      category: 'asc',
      value: sortState.map((columnSort: ColumnSort) => !columnSort.desc),
    },
    {
      category: 'sort',
      value: sortState.map((columnSort: ColumnSort) => columnSort.id),
    },
  ];
}
