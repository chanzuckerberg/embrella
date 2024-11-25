import {
  GRID_FILTER_ID,
  GridFilterConfig,
} from "@/views/GridsView/components/Main/components/GridFilter/filters/types";
import { GridFilterCategory } from "./types";
import {
  TOMOGRAM_FILTER_IDS,
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
export type EntityFilterId = TOMOGRAM_FILTER_IDS | GRID_FILTER_ID;

export type EntityFilterCategories =
  | GridFilterCategory
  | TomogramFilterCategory;

export type EntityFilterConfigs = TomogramFilterConfig | GridFilterConfig;
