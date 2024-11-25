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
