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
/*
 * Type for a formatted API response
 * Usage: EntityList<TomogramData, "tomograms">
 */

export type EntityList<T, K extends string> = {
  [entityName in K]: T[];
} & {
  pagination: Pagination;
  sortBy: SortBy;
};
