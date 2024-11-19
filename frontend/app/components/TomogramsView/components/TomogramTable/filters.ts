import {
  TOMOGRAM_FILTER_ID,
  TomogramFilterConfig,
} from "@app/common/types/filter";

export const TOMOGRAM_FILTER_CONFIGS: TomogramFilterConfig[][] = [
  [
    {
      filterCategory: "project",
      filterId: TOMOGRAM_FILTER_ID.PROJECT,
      label: "Project",
    },
    {
      filterCategory: "user",
      filterId: TOMOGRAM_FILTER_ID.USER,
      label: "User",
    },
    {
      filterCategory: "screeningSession",
      filterId: TOMOGRAM_FILTER_ID.SCREENING_SESSION,
      label: "Screening Session",
    },
    {
      filterCategory: "msiSession",
      filterId: TOMOGRAM_FILTER_ID.MSI_SESSION,
      label: "MSI Session",
    },
    {
      filterCategory: "date",
      filterId: TOMOGRAM_FILTER_ID.DATE,
      label: "Date",
    },
    {
      filterCategory: "procRun",
      filterId: TOMOGRAM_FILTER_ID.PROC_RUN,
      label: "Proc Run",
    },
  ],
];
