import { API, DJANGO_URL } from '@app/common/constants/api';

import { StorageSummary } from './types';

/**
 * Cluster-wide totals for the header strip.
 */
export const fetchStorageSummary = async (cluster?: string): Promise<StorageSummary> => {
  // Omitted rather than sent empty: the backend resolves its configured default
  // and reports which cluster that was, so there is nothing to guess at here.
  const query = cluster ? `?${new URLSearchParams({ cluster }).toString()}` : '';
  const response = await fetch(`${DJANGO_URL}${API.STORAGE_SESSIONS_SUMMARY}${query}`, {
    credentials: 'include',
  });
  if (!response.ok) {
    throw new Error(`Failed to load storage summary: ${response.statusText}`);
  }
  return response.json();
};
