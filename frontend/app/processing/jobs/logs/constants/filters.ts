import { JobFilterConfig, JobFilterId } from '../../monitor/types';

export const HISTORICAL_JOB_FILTER_CONFIGS: JobFilterConfig[][] = [
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
    {
      filterCategory: 'cluster',
      filterId: JobFilterId.CLUSTER,
      label: 'Cluster',
    },
  ],
  [
    {
      filterCategory: 'jobName',
      filterId: JobFilterId.JOB_NAME,
      label: 'Processor',
    },
    {
      filterCategory: 'completedDateRange',
      filterId: JobFilterId.COMPLETED_DATE_RANGE,
      label: 'Date Range',
    },
  ],
];
