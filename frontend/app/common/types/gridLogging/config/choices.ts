export interface ColorChoice {
  value: string;
  label: string;
}

export interface GridLoggingChoicesResponse {
  cane_colors: ColorChoice[];
  puck_colors: ColorChoice[];
  grid_box_colors: ColorChoice[];
  grid_box_numbering: ColorChoice[];
  // Box size → supported numbering codes; the first is the default.
  grid_box_numbering_by_size: Record<number, string[]>;
  grid_cassette_numbering: ColorChoice[];
}
