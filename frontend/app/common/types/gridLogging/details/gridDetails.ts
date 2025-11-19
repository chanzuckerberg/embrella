import { Specimen } from '../entities/specimenList';
import { FreezingSession } from '../entities/freezingSessionList';
import { Project } from '../entities/projectList';

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

export interface GridParameters {
  blot_time: number;
  blot_force: number;
  blot_distance: number;
}
