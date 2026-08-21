import {
  AnnotationFilterCategory,
  AnnotationFilterConfig,
  AnnotationFilterId,
} from '@app/components/AnnotationsView/types';
import { TomogramFilterId, TomogramFilterCategory, TomogramFilterConfig } from '@app/components/TomogramsView/types';
import { GridFilterCategory, GridFilterConfig, GridFilterId } from '@app/components/GridsView/types';
import {
  DirectoryFilterCategory,
  DirectoryFilterConfig,
  DirectoryFilterId,
} from '@app/components/DirectoryExplorerView/types';
import { ReviewFilterCategory } from '@app/components/ReviewsView/types';
import { SessionFilterCategory, SessionFilterConfig, SessionFilterId } from '@app/components/SessionBrowserView/types';
import { StorageFilterCategory, StorageFilterConfig, StorageFilterId } from '@app/components/StorageExplorerView/types';
import { JobFilterCategory, JobFilterConfig, JobFilterId } from '@app/processing/jobs/monitor/types';
import { ScreeningFilterCategory, ScreeningFilterConfig, ScreeningFilterId } from '@app/components/Screening/types';
// EntityFilterCategory extends EntityFilterCategories
export interface FiltersList<FilterCategory extends EntityFilterCategories> {
  filters: Record<FilterCategory, FilterOption[]>;
}

export interface FilterOption {
  name: boolean | string | null;
  count: number;
  selected: boolean;
}

// TODO: Consider moving these types under EntityTableFilters
export type EntityFilterIdTypes =
  | AnnotationFilterId
  | TomogramFilterId
  | GridFilterId
  | DirectoryFilterId
  | JobFilterId
  | ScreeningFilterId
  | SessionFilterId
  | StorageFilterId;

export type EntityFilterCategories =
  | AnnotationFilterCategory
  | GridFilterCategory
  | TomogramFilterCategory
  | DirectoryFilterCategory
  | ReviewFilterCategory
  | JobFilterCategory
  | ScreeningFilterCategory
  | SessionFilterCategory
  | StorageFilterCategory;

export type EntityFilterConfigs =
  | AnnotationFilterConfig
  | TomogramFilterConfig
  | GridFilterConfig
  | DirectoryFilterConfig
  | JobFilterConfig
  | ScreeningFilterConfig
  | SessionFilterConfig
  | StorageFilterConfig;

export interface FilterConfig<FilterId, FilterCategory extends string> {
  filterCategory: FilterCategory; // Key in result set row values to filter on.
  filterId: FilterId;
  label: string;
}

export type FilterState<FilterCategory extends string> = Partial<{
  [K in FilterCategory]: FilterValue[];
}>;

export type FilterValue = boolean | string | null;
