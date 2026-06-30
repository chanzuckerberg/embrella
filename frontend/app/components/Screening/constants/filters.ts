import { ScreeningFilterConfig, ScreeningFilterId } from '../types';

export const SCREENING_FILTER_CONFIGS: ScreeningFilterConfig[][] = [
  [
    {
      filterCategory: 'screeningStatus',
      filterId: ScreeningFilterId.STATUS,
      label: 'Status',
    },
    {
      filterCategory: 'microscope',
      filterId: ScreeningFilterId.MICROSCOPE,
      label: 'Microscope',
    },
    {
      filterCategory: 'priority',
      filterId: ScreeningFilterId.PRIORITY,
      label: 'Priority',
    },
  ],
  [
    {
      filterCategory: 'project',
      filterId: ScreeningFilterId.PROJECT,
      label: 'Project',
    },
  ],
];

export const SCREENING_FILTER_CATEGORIES = ['screeningStatus', 'microscope', 'priority', 'project'];
