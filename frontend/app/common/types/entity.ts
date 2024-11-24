import { TomogramData } from "@app/components/TomogramsView/types";
import { GridData } from "./types";

export interface EntityLinkField {
  id: number;
  name: string;
  url: string;
}

export type EntityAPIPrimaryAttributeToDataType = {
  tomograms: TomogramData;
  grid: GridData;
};
export interface MSISessionField {
  id: number;
  name: string;
  url: string;
}
