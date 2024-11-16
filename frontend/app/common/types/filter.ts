import { ComplexFilterProps as SDSComplexFilterProps } from "@czi-sds/components";
import { GridFilterCategory } from "./types";
import { FilterConfig } from "@/app/components/Filter/common/types";

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

export type TomogramFilterConfig = FilterConfig<
  TOMOGRAM_FILTER_ID,
  TomogramFilterCategory
>;

export enum TOMOGRAM_FILTER_ID {
  PROJECT = "PROJECT",
  USER = "USER",
  SCREENING_SESSION = "SCREENING_SESSION",
  MSI_SESSION = "MSI_SESSION",
  DATE = "DATE",
  PROC_RUN = "PROC_RUN",
}

export type ViewFilterCategory = GridFilterCategory | TomogramFilterCategory;
