import { StorageFilterConfig, StorageFilterId } from '../types';

/**
 * Sidebar filters. Categories must match `table_filters` in
 * processes/viewsets.py exactly — TableQueryFilter silently drops any it does
 * not recognise, so a typo here reads as a filter that does nothing.
 */
export const STORAGE_FILTER_CONFIGS: StorageFilterConfig[][] = [
  [
    {
      filterCategory: 'project',
      filterId: StorageFilterId.PROJECT,
      label: 'Project',
    },
    {
      filterCategory: 'user',
      filterId: StorageFilterId.USER,
      label: 'Session User',
    },
  ],
  [
    {
      // The filesystem owner, which often differs from the session's user.
      filterCategory: 'owner',
      filterId: StorageFilterId.OWNER,
      label: 'Filesystem Owner',
    },
    {
      filterCategory: 'processingSoftware',
      filterId: StorageFilterId.PROCESSING_SOFTWARE,
      label: 'Software',
    },
  ],
];

/**
 * Categories the URL-synced TableStateProvider tracks.
 *
 * Must be non-empty for TableStateProvider to pick its nuqs-backed branch at
 * all, and must include 'search' because the search bar dispatches into the
 * same filter state.
 */
export const STORAGE_FILTER_CATEGORIES = ['project', 'user', 'owner', 'processingSoftware', 'search'];
