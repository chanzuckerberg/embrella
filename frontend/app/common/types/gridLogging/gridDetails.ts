export interface GridDetailsResponse {
  grid_name: string;
  user: string;
  notes: string;
  clipped: boolean;
  trashed: boolean;
  location: GridLocation;
  freezing_session: FreezingSession | null;
  specimen: Specimen | null;
  project: Project | null;
  position_in_box: number;
  copy_number: number;
  parameters: GridParameters;
}

export interface GridLocation {
  puck_id: number;
  puck_name: string;
  grid_box_id: number;
  grid_box_name: string;
  position_in_box: number;
}

export interface FreezingSession {
  id: number;
  name: string;
  datetime: string;
  user: string;
  device: string | null;
  temperature: number | null;
  humidity: number | null;
}

export interface Specimen {
  id: number;
  name: string;
  samples: Sample[];
  notes: string;
}

export interface Sample {
  id: number;
  name: string;
  ontology: string;
}

export interface Project {
  id: number;
  name: string;
  description: string;
}

export interface GridParameters {
  blot_time: number;
  blot_force: number;
  blot_distance: number;
}
