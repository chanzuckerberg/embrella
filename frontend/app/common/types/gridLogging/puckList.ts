export interface PuckBase {
  user_id: number;
  name: string;
  color: string;
  cane: number;
  position_in_cane: number;
}

export interface pucksListResponse {
  total_pucks_count: number;
  pucks: PucksList[];
}

export interface PucksList extends PuckBase {
  id: number;
  name: string;
  color: string;
  color_display: string;
  position_in_cane: number;
  max_boxes: number;
  user_id: number;
  user_name: string;
  cane: number;
}

//Types for puck slots
export interface PuckSlotsResponse {
  puck_id: number;
  puck_name: string;
  slots: PuckSlots[];
  slot_summary: {
    total: number;
    filled_count: number;
    empty_count: number;
  };
}

export interface PuckSlots {
  position: number;
  status: string;
  grid_box_id?: number;
}

export type CreatePuckData = Omit<PuckBase, 'name'> & {
  puckName: string; // Frontend uses 'puckName' but API expects 'name'
};
