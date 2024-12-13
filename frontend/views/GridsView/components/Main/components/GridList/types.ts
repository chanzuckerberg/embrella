import { Pagination, SortBy } from "@/app/common/types/tableState";
import { GridData } from "@/app/common/types/types";

/*
 * Type for a formatted API response
 * Usage: EntityList<GridData, "grid">
 * TODO: this is only used for GridsView, should be removed in favor of version in tableState.ts
 */

export type EntityList<T, K extends string> = {
  [entityName in K]: T[];
} & {
  pagination: Pagination;
  sortBy: SortBy;
};
export interface Props {
  gridList?: EntityList<GridData, "grids">;
}
