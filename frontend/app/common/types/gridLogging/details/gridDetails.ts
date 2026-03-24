import { FreezingSessionDetail } from '../entities/freezingSessionList';
import { Specimen } from '../entities/specimenList';
import { ProjectData } from '../entities/projectList';

export interface GridDetailsResponse {
  grid_name: string;
  user: string;
  notes: string;
  clipped: boolean;
  trashed: boolean;
  location: GridLocation;
  freezing_session: FreezingSessionDetail | null;
  specimen: Specimen | null;
  project: ProjectData | null;
  position_in_box: number;
  copy_number: number;
  parameters: GridParameters;
  labels: { id: number; name: string; color: string }[];
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
