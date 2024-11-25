import { TomogramData } from "@app/components/TomogramsView/types";
import { GridData } from "./types";

export type EntityAPIPrimaryAttributeToDataType = {
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
