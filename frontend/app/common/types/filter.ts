import {
  AnnotationFilterCategory,
  AnnotationFilterConfig,
  AnnotationFilterId,
} from "@app/components/AnnotationsView/types";
import {
  TomogramFilterId,
  TomogramFilterCategory,
  TomogramFilterConfig,
} from "@app/components/TomogramsView/types";
import {
  GridFilterCategory,
  GridFilterConfig,
  GridFilterId,
} from "@app/components/GridsView/types";
// EntityFilterCategory extends EntityFilterCategories
export interface FiltersList<FilterCategory extends EntityFilterCategories> {
  filters: Record<FilterCategory, FilterOption[]>;
}
// export interface FiltersList<FilterCategory extends string> {
//   filters: Record<FilterCategory, FilterOption[]>;
// }

export interface FilterOption {
  name: boolean | string | null;
  count: number;
  selected: boolean;
}

// TODO: Consider moving these types under EntityTableFilters
export type EntityFilterIdTypes =
  | AnnotationFilterId
  | TomogramFilterId
  | GridFilterId;

export type EntityFilterCategories =
  | AnnotationFilterCategory
  | GridFilterCategory
  | TomogramFilterCategory;

export type EntityFilterConfigs =
  | AnnotationFilterConfig
  | TomogramFilterConfig
  | GridFilterConfig;
