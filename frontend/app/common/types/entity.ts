import { TomogramData } from "./tomogram";
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
