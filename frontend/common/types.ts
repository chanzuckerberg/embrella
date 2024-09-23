export interface ApiListResponse<T> {
  pagination: {
    page: number;
    pageSize: number;
    totalPages: number;
    totalResults: number;
  };
  result: T[];
}

export interface Configs {
  API_URL: string;
}

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
  msiSession: {
    id: number;
    name: string;
    url: string;
  }[];
}

export interface GridFreezingPlanSample {
  id: number;
  name: string;
  url: string;
}

export type SearchParam = Partial<Record<SEARCH_PARAM_NAME, unknown>>;

export enum SEARCH_PARAM_NAME {
  FILTER = "q",
  PAGINATION_PAGE = "page",
  PAGINATION_PAGE_SIZE = "pageSize",
  SORT_COLUMN_NAME = "sort",
  SORT_DIRECTION = "asc",
}
