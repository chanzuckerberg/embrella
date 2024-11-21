import { ComplexFilterProps as SDSComplexFilterProps } from "@czi-sds/components";
import { GridFilterCategory } from "./types";
import { FilterConfig } from "@/app/components/Filter/common/types";

export interface FiltersList {
  filters: Record<ViewFilterCategory, FilterOption[]>;
}

export interface FilterOption {
  name: boolean | string | null;
  count: number;
  selected: boolean;
}

export type TomogramFilterCategory =
  | "project"
  | "sample"
  | "user"
  | "msiSession"
  | "screeningSession"
  | "procPlan"
  | "date";

export type TomogramFilterConfig = FilterConfig<
  TOMOGRAM_FILTER_ID,
  TomogramFilterCategory
>;

export enum TOMOGRAM_FILTER_ID {
  PROJECT = "PROJECT",
  SAMPLE = "SAMPLE",
  USER = "USER",
  MSI_SESSION = "MSI_SESSION",
  SCREENING_SESSION = "SCREENING_SESSION",
  PROC_PLAN = "PROC_PLAN",
  DATE = "DATE",
}

export type ViewFilterCategory = GridFilterCategory | TomogramFilterCategory;
