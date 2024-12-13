import {
  EntityLinkField,
  GridField,
  MSISessionField,
  ProcRunField,
  UserField,
} from "@app/common/types/entity";
import { FilterConfig } from "@app/components/Filter/common/types";

export interface TomogramData {
  tomograms: EntityLinkField;
  procPlan: EntityLinkField;
  procRun: ProcRunField;
  json: null;
  grid: GridField;
  project: EntityLinkField;
  user: UserField;
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
