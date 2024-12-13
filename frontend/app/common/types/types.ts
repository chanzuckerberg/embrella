import { FilterOption } from "./filter";
import { MSISessionField } from "./entity";

// This type is used in GridsView
export interface FiltersList<FilterCategory extends string> {
  filters: Record<FilterCategory, FilterOption[]>;
}

export type GridFilterCategory =
  | "cassette"
  | "date"
  | "msiSession"
  | "project"
  | "puck"
  | "sample"
  | "screeningSession"
  | "status"
  | "user";

export interface GridData {
  grid: {
    id: number;
    createdAt: string;
    name: string;
    trashed: boolean;
    updatedAt: string | null;
    url: string;
  };
  cassette: {
    name: string;
  };
  project: {
    id: number;
    name: string;
    url: string;
  };
  puck: {
    name: string;
  };
  user: {
    id: number;
    name: string;
  };
  freezingPlan: {
    id: number;
    sample: GridFreezingPlanSample[];
  };
  freezingSession: {
    id: number;
    createdAt: string;
  };
  screeningSession: string;
  msiSession: MSISessionField[];
}

export interface GridFreezingPlanSample {
  id: number;
  name: string;
  url: string;
}
