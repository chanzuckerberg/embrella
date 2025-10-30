import { GridBoxDetail, Position } from './gridBox';

export interface GridBoxDetailResponse {
  puck_id: number;
  puck_name: string;
  position_in_puck: number;
  status: 'filled' | 'empty';
  max_grids?: number;
  grid_box?: GridBoxDetail;
}

// Re-export for backward compatibility
export type { GridBoxDetail as GridBox, Position } from './gridBox';