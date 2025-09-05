export interface pucksListResponse {
    total_pucks_count: number;
    pucks: PucksList[];
  }
  
  export interface PucksList {
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
