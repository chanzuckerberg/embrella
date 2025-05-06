import { GridFilterConfig, GridFilterId } from '../types';

export const GRID_FILTER_CONFIGS: GridFilterConfig[][] = [
  [
    {
      filterCategory: 'project',
      filterId: GridFilterId.PROJECT,
      label: 'Project',
    },
    {
      filterCategory: 'puck',
      filterId: GridFilterId.PUCK,
      label: 'Puck',
    },
    {
      filterCategory: 'sample',
      filterId: GridFilterId.SAMPLE,
      label: 'Sample',
    },
    {
      filterCategory: 'user',
      filterId: GridFilterId.USER,
      label: 'User',
    },
    {
      filterCategory: 'cassette',
      filterId: GridFilterId.CASSETTE,
      label: 'Cassette',
    },
    {
      filterCategory: 'date',
      filterId: GridFilterId.DATE,
      label: 'Date',
    },
  ],
  [
    {
      filterCategory: 'screeningSession',
      filterId: GridFilterId.SCREENING_SESSION,
      label: 'Screening Session',
    },
    {
      filterCategory: 'msiSession',
      filterId: GridFilterId.MSI_SESSION,
      label: 'MSI Session',
    },
  ],
  [
    {
      filterCategory: 'status',
      filterId: GridFilterId.STATUS,
      label: 'Status',
    },
  ],
];
