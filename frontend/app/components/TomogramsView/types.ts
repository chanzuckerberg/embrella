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

export enum TomogramFilterId {
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
  TomogramFilterId,
  TomogramFilterCategory
>;

export const TOMOGRAM_FILTER_CONFIGS: TomogramFilterConfig[][] = [
  [
    {
      filterCategory: "project",
      filterId: TomogramFilterId.PROJECT,
      label: "Project",
    },
    {
      filterCategory: "sample",
      filterId: TomogramFilterId.SAMPLE,
      label: "Sample",
    },
    {
      filterCategory: "user",
      filterId: TomogramFilterId.USER,
      label: "User",
    },
    {
      filterCategory: "msiSession",
      filterId: TomogramFilterId.MSI_SESSION,
      label: "MSI Session",
    },
    {
      filterCategory: "screeningSession",
      filterId: TomogramFilterId.SCREENING_SESSION,
      label: "Screening Session",
    },
    {
      filterCategory: "procPlan",
      filterId: TomogramFilterId.PROC_PLAN,
      label: "Proc Plan",
    },
    {
      filterCategory: "date",
      filterId: TomogramFilterId.DATE,
      label: "Date",
    },
  ],
];
