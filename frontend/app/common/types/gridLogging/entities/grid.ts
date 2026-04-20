// Grid creation types
export interface CreateGridData {
  grid_box: number;
  name: string;
  user: number;
  specimen: number;
  intended_project: number;
  position_in_box: number;
  freezing_session?: number;
  notes?: string;
  clipped?: boolean;
  blot_time?: number;
  blot_force?: number;
  blot_distance?: number;
  copy_number?: number;
}

export interface GridCreateResponse {
  id: number;
  name: string;
  user: number;
  specimen: number;
  intended_project: number;
  grid_box: number;
  position_in_box: number;
  freezing_session?: number;
  notes?: string;
  clipped: boolean;
  trashed: boolean;
  blot_time?: number;
  blot_force?: number;
  blot_distance?: number;
  copy_number: number;
}

// Grid move types
export interface MoveGridData {
  grid_id: number;
  destination_grid_box_id: number;
  destination_position: number;
}

export interface MoveGridResponse {
  success: boolean;
  message: string;
  grid: {
    id: number;
    name: string;
    grid_box: number;
    position_in_box: number;
    user: number;
    specimen: number;
    freezing_session: number;
    clipped: boolean;
    trashed: boolean;
  };
}

// Grid duplicate types
export interface DuplicateGridData {
  grid_id: number;
  destination_grid_box_id: number;
  number_to_copy: number;
}

export interface DuplicateGridResponse {
  success: boolean;
  message: string;
  new_grid_ids: number[];
  grids: GridCreateResponse[];
}

export interface AvailablePositionsResponse {
  box_id: number;
  max_grids: number;
  used_positions: number[];
  available_positions: number[];
  available_count: number;
}
