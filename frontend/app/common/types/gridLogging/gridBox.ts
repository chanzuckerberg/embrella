/**
 * Position in a grid box
 */
export interface Position {
  q: number;
  occupied: boolean;
  grid_id?: number;
  grid_name?: string;
  clipped?: boolean;
}

/**
 * Base grid box properties shared across different API responses
 */
export interface GridBoxBase {
  name: string;
  color: string;
  color_display: string;
  numbering: string;
  numbering_display: string;
  max_grids: number;
}

/**
 * Grid box response from creation endpoint
 */
export interface GridBoxCreateResponse extends GridBoxBase {
  id: number;
  position_in_puck: number;
  puck: number;
  puck_user?: string;
}

/**
 * Grid box with detailed information including positions
 * Used in grid box detail view
 */
export interface GridBoxDetail extends GridBoxBase {
  grid_box_id: number;
  positions: Position[];
}
