import { TomogramFilterConfig, TomogramFilterId } from '../types';

export const TOMOGRAM_FILTER_CONFIGS: TomogramFilterConfig[][] = [
  [
    {
      filterCategory: 'project',
      filterId: TomogramFilterId.PROJECT,
      label: 'Project',
    },
    {
      filterCategory: 'sample',
      filterId: TomogramFilterId.SAMPLE,
      label: 'Sample',
    },
    {
      filterCategory: 'user',
      filterId: TomogramFilterId.USER,
      label: 'User',
    },
    {
      filterCategory: 'msiSession',
      filterId: TomogramFilterId.MSI_SESSION,
      label: 'MSI Session',
    },
    {
      filterCategory: 'screeningSession',
      filterId: TomogramFilterId.SCREENING_SESSION,
      label: 'Screening Session',
    },
    {
      filterCategory: 'procPlan',
      filterId: TomogramFilterId.PROC_PLAN,
      label: 'Proc Plan',
    },
    {
      filterCategory: 'date',
      filterId: TomogramFilterId.DATE,
      label: 'Date',
    },
  ],
];
