import { AnnotationData } from '@app/components/AnnotationsView/types';
import { DirectorySummary } from '@app/components/DirectoryExplorerView/types';
import { GridData } from '@app/components/GridsView/types';
import { ReviewData } from '@app/components/ReviewsView/types';
import { TomogramData } from '@app/components/TomogramsView/types';
import { Job } from '@app/processing/monitor/types';

export type EntityDataTypes = AnnotationData | DirectorySummary | GridData | TomogramData | ReviewData | Job;

/*
 * Type for a formatted API response
 * Usage: EntityList<TomogramData, "tomograms">
 */
export type EntityList<T extends EntityDataTypes> = {
  entities: T[];
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
}

/*
 * For a raw API response
 */
export interface ApiListResponse<T> {
  pagination: Pagination;
  result: T[];
  sortBy: SortBy;
}
