import { AnnotationData } from '@app/components/AnnotationsView/types';
import { DirectorySummary } from '@app/components/DirectoryExplorerView/types';
import { GridBoxData } from '@app/components/GridInventory/GridBoxesView/types';
import { PuckData } from '@app/components/GridInventory/PucksView/types';
import { ScreeningGridData } from '@app/components/Screening/types';
import { StandardSampleData } from '@app/components/StandardSamples/types';
import { GridData } from '@app/components/GridsView/types';
import { ReviewData } from '@app/components/ReviewsView/types';
import { SessionOverviewData } from '@app/components/SessionBrowserView/types';
import { TomogramData } from '@app/components/TomogramsView/types';
import { Job } from '@app/processing/jobs/monitor/types';

export type EntityDataTypes =
  | AnnotationData
  | DirectorySummary
  | GridBoxData
  | GridData
  | PuckData
  | SessionOverviewData
  | StandardSampleData
  | ScreeningGridData
  | TomogramData
  | ReviewData
  | Job;

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
