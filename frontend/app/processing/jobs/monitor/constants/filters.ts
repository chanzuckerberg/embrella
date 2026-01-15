import { JobFilterConfig, JobFilterId } from '../types';

export const JOB_FILTER_CONFIGS: JobFilterConfig[][] = [
  [
    {
      filterCategory: 'user',
      filterId: JobFilterId.USER,
      label: 'User',
    },
    {
      filterCategory: 'status',
      filterId: JobFilterId.STATUS,
      label: 'Status',
    },
  ],
  [
    {
      filterCategory: 'partition',
      filterId: JobFilterId.PARTITION,
      label: 'Partition',
    },
    {
      filterCategory: 'completedDateRange',
      filterId: JobFilterId.COMPLETED_DATE_RANGE,
      label: 'Completed Date Range',
    },
  ],
];
