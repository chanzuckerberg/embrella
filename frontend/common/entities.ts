export interface Configs {
  API_URL: string;
}

export interface Grid {
  grid: {
    id: number;
    name: string;
    trashed: boolean;
    url: string;
    created: string;
  };
  cassette: {
    name: string;
  };
  project: {
    id: string;
    name: string;
    url: string;
  };
  puck: {
    name: string;
  };
  user: {
    id: string;
    name: string;
  };
  freezingPlan: {
    id: number;
    sample: string;
  };
  freezingSession: {
    id: number;
    created: string;
  };
  screeningSession: string;
  msiSession: {
    id: number;
    name: string;
    url: string;
  }[];
}
