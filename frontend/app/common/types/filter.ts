import {
  AnnotationFilterCategory,
  AnnotationFilterConfig,
  AnnotationFilterId,
} from "@app/components/AnnotationsView/types";
import {
  GRID_FILTER_ID,
  GridFilterConfig,
} from "@/views/GridsView/components/Main/components/GridFilter/filters/types";
import { GridFilterCategory } from "./types";
import {
  TomogramFilterId,
  TomogramFilterCategory,
  TomogramFilterConfig,
} from "@app/components/TomogramsView/types";

export interface FiltersList {
  filters: Record<EntityFilterCategories, FilterOption[]>;
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
  | GRID_FILTER_ID;

export type EntityFilterCategories =
  | AnnotationFilterCategory
  | GridFilterCategory
  | TomogramFilterCategory;

export type EntityFilterConfigs =
  | AnnotationFilterConfig
  | TomogramFilterConfig
  | GridFilterConfig;
