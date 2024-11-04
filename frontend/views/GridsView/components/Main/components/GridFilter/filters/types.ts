import { FilterConfig } from "@/app/components/Filter/common/types";
import { GridFilterCategory } from "@/app/common/types/types";

export type GridFilterConfig = FilterConfig<GRID_FILTER_ID, GridFilterCategory>;

export enum GRID_FILTER_ID {
  CASSETTE = "CASSETTE",
  DATE = "DATE",
  MSI_SESSION = "MSI_SESSION",
  PROJECT = "PROJECT",
  PUCK = "PUCK",
  SAMPLE = "SAMPLE",
  SCREENING_SESSION = "SCREENING_SESSION",
  STATUS = "STATUS",
  USER = "USER",
}
