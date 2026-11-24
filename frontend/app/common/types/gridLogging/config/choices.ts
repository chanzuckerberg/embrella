export interface ColorChoice {
  value: string;
  label: string;
}

export interface GridBoxDefaults {
  max_grids: number;
  color: string;
  numbering: string;
}

export interface GridLoggingChoicesResponse {
  cane_colors: ColorChoice[];
  puck_colors: ColorChoice[];
  grid_box_colors: ColorChoice[];
  grid_box_numbering: ColorChoice[];
  // Box size → supported numbering codes; the first is the default.
  grid_box_numbering_by_size: Record<number, string[]>;
  // Initial values for a new grid box, e.g. { max_grids: 8, color: '00cdf5', numbering: 'col' }.
  grid_box_defaults: GridBoxDefaults;
  grid_cassette_numbering: ColorChoice[];
}
