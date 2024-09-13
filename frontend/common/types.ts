export interface ApiListResponse<T> {
  result: T[];
}

export interface Configs {
  API_URL: string;
}

export interface FiltersList {
  filters: Record<FilterName, FilterOption[]>;
}

export type FilterName =
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
  name: string | null;
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
