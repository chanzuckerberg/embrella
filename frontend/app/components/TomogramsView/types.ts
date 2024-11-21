import { FilterConfig } from "@app/components/Filter/common/types";

export enum TOMOGRAM_FILTER_ID {
  PROJECT = "PROJECT",
  SAMPLE = "SAMPLE",
  USER = "USER",
  MSI_SESSION = "MSI_SESSION",
  SCREENING_SESSION = "SCREENING_SESSION",
  PROC_PLAN = "PROC_PLAN",
  DATE = "DATE",
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

export const TOMOGRAM_FILTER_CONFIGS: TomogramFilterConfig[][] = [
  [
    {
      filterCategory: "project",
      filterId: TOMOGRAM_FILTER_ID.PROJECT,
      label: "Project",
    },
    {
      filterCategory: "sample",
      filterId: TOMOGRAM_FILTER_ID.SAMPLE,
      label: "Sample",
    },
    {
      filterCategory: "user",
      filterId: TOMOGRAM_FILTER_ID.USER,
      label: "User",
    },
    {
      filterCategory: "msiSession",
      filterId: TOMOGRAM_FILTER_ID.MSI_SESSION,
      label: "MSI Session",
    },
    {
      filterCategory: "screeningSession",
      filterId: TOMOGRAM_FILTER_ID.SCREENING_SESSION,
      label: "Screening Session",
    },
    {
      filterCategory: "procPlan",
      filterId: TOMOGRAM_FILTER_ID.PROC_PLAN,
      label: "Proc Plan",
    },
    {
      filterCategory: "date",
      filterId: TOMOGRAM_FILTER_ID.DATE,
      label: "Date",
    },
  ],
];
