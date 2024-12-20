import {
  EntityLinkField,
  GridField,
  MSISessionField,
  // ProcRunField,
  UserField,
} from "@app/common/types/entity";
import { FilterConfig } from "@app/common/components/Filter/common/types";

interface AnnotationsField extends EntityLinkField {
  updatedAt: string;
  notes: string;
}
export interface AnnotationData {
  annotations: AnnotationsField;
  procPlan: EntityLinkField;
  inputTomogram: EntityLinkField;
  json: null;
  grid: GridField;
  project: EntityLinkField;
  user: UserField;
  msiSession: MSISessionField;
}
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
