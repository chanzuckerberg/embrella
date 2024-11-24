import { TomogramData } from "./tomogram";
import { GridData } from "./types";

export type EntityDataTypes = GridData | TomogramData;

/*
 * Type for a formatted API response
 * Usage: EntityList<TomogramData, "tomograms">
 */
export type EntityList = {
  entities: EntityDataTypes[];
  pagination: Pagination;
  sortBy: SortBy;
};

export interface Pagination {
  page: number;
  pageSize: number;
  totalPages: number;
  totalResults: number;
}

export interface SortBy {
  asc: boolean;
  sort: string;
} /*
 * For a raw API response
 */

export interface ApiListResponse<T> {
  pagination: Pagination;
  result: T[];
  sortBy: SortBy;
}
