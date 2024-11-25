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

export enum TOMOGRAM_FILTER_IDS {
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
  TOMOGRAM_FILTER_IDS,
  TomogramFilterCategory
>;

export const TOMOGRAM_FILTER_CONFIGS: TomogramFilterConfig[][] = [
  [
    {
      filterCategory: "project",
      filterId: TOMOGRAM_FILTER_IDS.PROJECT,
      label: "Project",
    },
    {
      filterCategory: "sample",
      filterId: TOMOGRAM_FILTER_IDS.SAMPLE,
      label: "Sample",
    },
    {
      filterCategory: "user",
      filterId: TOMOGRAM_FILTER_IDS.USER,
      label: "User",
    },
    {
      filterCategory: "msiSession",
      filterId: TOMOGRAM_FILTER_IDS.MSI_SESSION,
      label: "MSI Session",
    },
    {
      filterCategory: "screeningSession",
      filterId: TOMOGRAM_FILTER_IDS.SCREENING_SESSION,
      label: "Screening Session",
    },
    {
      filterCategory: "procPlan",
      filterId: TOMOGRAM_FILTER_IDS.PROC_PLAN,
      label: "Proc Plan",
    },
    {
      filterCategory: "date",
      filterId: TOMOGRAM_FILTER_IDS.DATE,
      label: "Date",
    },
  ],
];
