import { FreezingSessionDetail } from '../entities/freezingSessionList';
import { Specimen } from '../entities/specimenList';
import { ProjectData } from '../entities/projectList';

export interface GridDetailsResponse {
  id: number;
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
  labels: GridLabelDetail[];
  created_on: string;
  updated_on: string;
}

export interface GridLabelDetail {
  id: number;
  name: string;
  color: string;
  added_at: string | null;
  added_by: string | null;
}

export interface GridLocation {
  puck_id: number;
  puck_name: string;
  puck_color: string | null;
  grid_box_id: number;
  grid_box_name: string;
  position_in_box: number;
  position_in_puck: number | null;
}

export interface GridParameters {
  blot_time: number;
  blot_force: number;
  blot_distance: number;
}
