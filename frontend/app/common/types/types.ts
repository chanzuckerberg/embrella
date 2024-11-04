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

export interface FilterOption {
  name: boolean | string | null;
  count: number;
  selected: boolean;
}

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

export interface Pagination {
  page: number;
  pageSize: number;
  totalPages: number;
  totalResults: number;
}

export interface SortBy {
  asc: boolean;
  sort: string;
}
