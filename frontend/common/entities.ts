export interface ApiListResponse<T> {
  Result: T[];
}

export interface Configs {
  API_URL: string;
}

export interface GridData {
  grid: {
    id: number;
    name: string;
    trashed: boolean;
    url: string;
    created_at: string;
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
    sample: string[];
  };
  freezingSession: {
    id: number;
    created_at: string;
  };
  screeningSession: string;
  msiSession: {
    id: number;
    name: string;
    url: string;
  }[];
}
