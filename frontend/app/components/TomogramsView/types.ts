import { EntityLinkField, MSISessionField } from "@app/common/types/entity";
import { FilterConfig } from "@app/components/Filter/common/types";

export interface TomogramData {
  tomograms: EntityLinkField;
  procPlan: EntityLinkField;
  procRun: {
    id: number;
    notes: string;
    createdAt: string;
  };
  json: null;
  grid: {
    id: number;
    name: string;
    trashed: boolean;
    url: string;
    createdAt: string;
  };
  project: EntityLinkField;
  user: {
    id: number;
    name: string;
  };
  msiSession: MSISessionField;
}

export enum TomogramFilterIds {
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
  TomogramFilterIds,
  TomogramFilterCategory
>;

export const TOMOGRAM_FILTER_CONFIGS: TomogramFilterConfig[][] = [
  [
    {
      filterCategory: "project",
      filterId: TomogramFilterIds.PROJECT,
      label: "Project",
    },
    {
      filterCategory: "sample",
      filterId: TomogramFilterIds.SAMPLE,
      label: "Sample",
    },
    {
      filterCategory: "user",
      filterId: TomogramFilterIds.USER,
      label: "User",
    },
    {
      filterCategory: "msiSession",
      filterId: TomogramFilterIds.MSI_SESSION,
      label: "MSI Session",
    },
    {
      filterCategory: "screeningSession",
      filterId: TomogramFilterIds.SCREENING_SESSION,
      label: "Screening Session",
    },
    {
      filterCategory: "procPlan",
      filterId: TomogramFilterIds.PROC_PLAN,
      label: "Proc Plan",
    },
    {
      filterCategory: "date",
      filterId: TomogramFilterIds.DATE,
      label: "Date",
    },
  ],
];
