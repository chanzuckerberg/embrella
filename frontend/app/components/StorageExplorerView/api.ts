import { API, DJANGO_URL } from '@app/common/constants/api';
import { postResource } from '@app/common/queries/fetchResource';

import { SettableStatus, StorageSummary } from './types';

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

/**
 * Record a preservation decision over one or more directories.
 *
 * `unset` clears the rows rather than storing the word, so a run underneath
 * falls back to whatever an ancestor decided.
 */
export const recordStorageDecision = async (
  cluster: string,
  pathPrefixes: string[],
  status: SettableStatus,
  notes = ''
): Promise<void> => {
  const response = await postResource(`${DJANGO_URL}${API.STORAGE_DECISIONS}`, {
    cluster,
    path_prefixes: pathPrefixes,
    status,
    notes,
  });

  if (!response.ok) {
    // The backend rejects a prefix that is not under a surveyed root or matches nothing on disk
    const detail = await response.json().catch(() => null);
    throw new Error(detail ? JSON.stringify(detail) : `Failed to record decision: ${response.statusText}`);
  }
};
