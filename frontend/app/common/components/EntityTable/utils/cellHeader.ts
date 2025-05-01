import { Header, RowData, SortDirection } from '@tanstack/react-table';
import { CellHeaderDirection } from '@czi-sds/components';

/**
 * Returns cell header active state.
 * @param header - Header.
 * @returns cell header active state.
 */
export function getCellHeaderActive<TData extends RowData, TValue>(header: Header<TData, TValue>): boolean {
  return Boolean(header.column.getCanSort() && header.column.getIsSorted());
}

/**
 * Returns cell header sort direction.
 * @param header - Header.
 * @returns cell header sort direction.
 */
export function getCellHeaderDirection<TData extends RowData, TValue>(
  header: Header<TData, TValue>
): CellHeaderDirection | undefined {
  const isSorted = header.column.getIsSorted();
  if (isCellHeaderDirection(isSorted)) {
    return isSorted;
  }
}

/**
 * Returns cell header hide sort icon state.
 * @param header - Header.
 * @returns cell header hide sort icon state.
 */
export function getCellHeaderHideSortIcon<TData extends RowData, TValue>(header: Header<TData, TValue>): boolean {
  return !header.column.getCanSort();
}

/**
 * Returns true, if value is CellHeaderDirection.
 * @param value - Value.
 * @returns true if value is CellHeaderDirection.
 */
function isCellHeaderDirection(value: SortDirection | false): value is CellHeaderDirection {
  if (value === false) return false;
  return ['asc', 'desc'].includes(value);
}
