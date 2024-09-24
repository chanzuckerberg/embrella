import {
  GRID_FILTER_ID,
  GridFilterConfig,
} from "@/views/GridsView/components/GridFilter/filters/types";

export const GRID_FILTER_CONFIG_CASSETTE: GridFilterConfig = {
  filterCategory: "cassette",
  filterId: GRID_FILTER_ID.CASSETTE,
  label: "Cassette",
};

export const GRID_FILTER_CONFIG_DATE: GridFilterConfig = {
  filterCategory: "date",
  filterId: GRID_FILTER_ID.DATE,
  label: "Date",
};

export const GRID_FILTER_CONFIG_MSI_SESSION: GridFilterConfig = {
  filterCategory: "msiSession",
  filterId: GRID_FILTER_ID.MSI_SESSION,
  label: "MSI Session",
};

export const GRID_FILTER_CONFIG_PROJECT: GridFilterConfig = {
  filterCategory: "project",
  filterId: GRID_FILTER_ID.PROJECT,
  label: "Project",
};

export const GRID_FILTER_CONFIG_PUCK: GridFilterConfig = {
  filterCategory: "puck",
  filterId: GRID_FILTER_ID.PUCK,
  label: "Puck",
};

export const GRID_FILTER_CONFIG_SAMPLE: GridFilterConfig = {
  filterCategory: "sample",
  filterId: GRID_FILTER_ID.SAMPLE,
  label: "Sample",
};

export const GRID_FILTER_CONFIG_SCREENING_SESSION: GridFilterConfig = {
  filterCategory: "screeningSession",
  filterId: GRID_FILTER_ID.SCREENING_SESSION,
  label: "Screening Session",
};

export const GRID_FILTER_CONFIG_STATUS: GridFilterConfig = {
  filterCategory: "status",
  filterId: GRID_FILTER_ID.STATUS,
  label: "Status",
};

export const GRID_FILTER_CONFIG_USER: GridFilterConfig = {
  filterCategory: "user",
  filterId: GRID_FILTER_ID.USER,
  label: "User",
};

export const GRID_FILTER_CONFIG: Record<
  keyof typeof GRID_FILTER_ID,
  GridFilterConfig
> = {
  CASSETTE: GRID_FILTER_CONFIG_CASSETTE,
  DATE: GRID_FILTER_CONFIG_DATE,
  MSI_SESSION: GRID_FILTER_CONFIG_MSI_SESSION,
  PROJECT: GRID_FILTER_CONFIG_PROJECT,
  PUCK: GRID_FILTER_CONFIG_PUCK,
  SAMPLE: GRID_FILTER_CONFIG_SAMPLE,
  SCREENING_SESSION: GRID_FILTER_CONFIG_SCREENING_SESSION,
  STATUS: GRID_FILTER_CONFIG_STATUS,
  USER: GRID_FILTER_CONFIG_USER,
};

export const GRID_FILTER_CONFIGS: GridFilterConfig[][] = [
  [
    GRID_FILTER_CONFIG.PROJECT,
    GRID_FILTER_CONFIG.PUCK,
    GRID_FILTER_CONFIG.SAMPLE,
    GRID_FILTER_CONFIG.USER,
    GRID_FILTER_CONFIG.CASSETTE,
    GRID_FILTER_CONFIG.DATE,
  ],
  [GRID_FILTER_CONFIG.SCREENING_SESSION, GRID_FILTER_CONFIG.MSI_SESSION],
  [GRID_FILTER_CONFIG.STATUS],
];
