import { ComplexFilterProps as SDSComplexFilterProps } from "@czi-sds/components";
import { GridFilterCategory } from "./types";

export interface FilterOption {
  name: boolean | string | null;
  count: number;
  selected: boolean;
}

export interface FiltersList<FilterCategory extends string> {
  filters: Record<FilterCategory, FilterOption[]>;
}

export type TomogramFilterCategory =
  | "project"
  | "user"
  | "screeningSession"
  | "msiSession"
  | "date"
  | "procRun";

export type ViewFilterCategory = GridFilterCategory | TomogramFilterCategory;
