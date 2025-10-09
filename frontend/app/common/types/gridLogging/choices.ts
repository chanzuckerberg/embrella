export interface ColorChoice {
    value: string;
    label: string;
}

export interface GridLoggingChoicesResponse {
    cane_colors: ColorChoice[];
    puck_colors: ColorChoice[];
    grid_box_colors: ColorChoice[];
    grid_box_numbering: ColorChoice[];
    grid_cassette_numbering: ColorChoice[];
}