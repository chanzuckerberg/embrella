import {
  EntityLinkField,
  GridField,
  MSISessionField,
  ProcRunField,
  UserField,
} from "@app/common/types/entity";
import { FilterConfig } from "@app/components/Filter/common/types";

export interface AnnotationData {
  annotations: EntityLinkField;
  procPlan: EntityLinkField;
  procRun: ProcRunField;
  json: null;
  grid: GridField;
  project: EntityLinkField;
  user: UserField;
  msiSession: MSISessionField;
  //TODO: need tomograms field?
}

//TODO: need tomograms field for all filter types below?
export enum AnnotationFilterId {
  PROJECT = "PROJECT",
  SAMPLE = "SAMPLE",
  USER = "USER",
  SCREENING_SESSION = "SCREENING_SESSION",
  MSI_SESSION = "MSI_SESSION",
  DATE = "DATE",
  PROC_PLAN = "PROC_PLAN",
}

export type AnnotationFilterCategory =
  | "project"
  | "sample"
  | "user"
  | "screeningSession"
  | "msiSession"
  | "date"
  | "procPlan";

export type AnnotationFilterConfig = FilterConfig<
  AnnotationFilterId,
  AnnotationFilterCategory
>;
