import { ComplexFilterProps as SDSComplexFilterProps } from "@czi-sds/components";
import { GridFilterCategory } from "./types";
import { TomogramFilterCategory } from "@app/components/TomogramsView/components/TomogramTable/filters";

export interface FiltersList {
  filters: Record<ViewFilterCategory, FilterOption[]>;
}

export interface FilterOption {
  name: boolean | string | null;
  count: number;
  selected: boolean;
}

export type ViewFilterCategory = GridFilterCategory | TomogramFilterCategory;
