import { MSISession } from "./msiSession";

export interface ApiListResponse<T> {
  pagination: Pagination;
  result: T[];
  sortBy: SortBy;
}

export type EntityList<T, K extends string> = {
  [entityName in K]: T[];
} & {
  pagination: Pagination;
  sortBy: SortBy;
};

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
  msiSession: MSISession[];
}

export interface GridFreezingPlanSample {
  id: number;
  name: string;
  url: string;
}

// TODO: Move to state types file
export interface Pagination {
  page: number;
  pageSize: number;
  totalPages: number;
  totalResults: number;
}

// TODO: Move to state types file
export interface SortBy {
  asc: boolean;
  sort: string;
}
