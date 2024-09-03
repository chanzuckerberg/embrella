import { GridData } from "@/common/types";

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
