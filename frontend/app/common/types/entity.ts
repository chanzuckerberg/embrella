import { AnnotationData } from "./../../components/AnnotationsView/types";
import { TomogramData } from "@app/components/TomogramsView/types";
import { GridData } from "./types";

export type EntityAPIPrimaryAttributeToDataType = {
  annotations: AnnotationData;
  tomograms: TomogramData;
  grid: GridData;
};

export interface EntityLinkField {
  id: number;
  name: string;
  url: string;
}

export interface MSISessionField {
  id: number;
  name: string;
  url: string;
}

export interface GridField {
  id: number;
  name: string;
  trashed: boolean;
  url: string;
  createdAt: string;
}

export interface ProcRunField {
  id: number;
  notes: string;
  updatedAt: string;
}

export interface UserField {
  id: number;
  name: string;
}
