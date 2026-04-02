export interface GridBoxChildGridLabel {
  id: number;
  name: string;
  color: string;
}

export interface GridBoxChildGrid {
  id: number;
  name: string;
  position_in_box: number | null;
  clipped: boolean;
  trashed: boolean;
  notes: string | null;
  user_name: string | null;
  specimen_samples: string[];
  project_name: string | null;
  labels: GridBoxChildGridLabel[];
  create_on: string | null;
}

export interface GridBoxData {
  gridBox: {
    id: number;
    name: string;
  };
  color: string;
  colorDisplay: string;
  numberingDisplay: string;
  puckName: string | null;
  positionInPuck: number | null;
  maxGrids: number;
  gridCount: number;
  puckUser: string | null;
  grids: GridBoxChildGrid[];
}
