import { DirectoryFilterConfig, DirectoryFilterId } from '../types';

export const DIRECTORY_FILTER_CONFIGS: DirectoryFilterConfig[][] = [
  [
    {
      filterCategory: 'cluster',
      filterId: DirectoryFilterId.CLUSTER,
      label: 'Cluster',
    },
    {
      filterCategory: 'origin',
      filterId: DirectoryFilterId.ORIGIN,
      label: 'Origin',
    },
    {
      filterCategory: 'preserve_status',
      filterId: DirectoryFilterId.PRESERVE_STATUS,
      label: 'Status',
    },
    {
      filterCategory: 'owner_username',
      filterId: DirectoryFilterId.OWNER,
      label: 'Owner',
    },
  ],
];
