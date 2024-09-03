export interface ApiListResponse<T> {
  result: T[];
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
    createdAt: string;
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
