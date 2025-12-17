import { API, DJANGO_URL, POST_API } from '@app/common/constants/api';

import {
  DirectoriesResponse,
  DirectoryFilesResponse,
  DirectoryStats,
  FilesystemSurvey,
  PreserveStatus,
  SurveysResponse,
} from './types';

/**
 * Fetch all filesystem surveys.
 */
export const fetchSurveys = async (cluster?: string, status?: string): Promise<SurveysResponse> => {
  const params = new URLSearchParams();
  if (cluster) params.append('cluster', cluster);
  if (status) params.append('status', status);

  const queryString = params.toString();
  const suffix = queryString ? `?${queryString}` : '';
  const url = `${DJANGO_URL}${API.SURVEYS}${suffix}`;

  const response = await fetch(url, { credentials: 'include' });
  if (!response.ok) {
    throw new Error(`Failed to fetch surveys: ${response.statusText}`);
  }
  return response.json();
};

/**
 * Fetch a single survey by ID.
 */
export const fetchSurvey = async (surveyId: number): Promise<FilesystemSurvey> => {
  const url = `${DJANGO_URL}${API.SURVEYS}/${surveyId}/`;
  const response = await fetch(url, { credentials: 'include' });
  if (!response.ok) {
    throw new Error(`Failed to fetch survey: ${response.statusText}`);
  }
  return response.json();
};

/**
 * Fetch directory statistics for a survey.
 */
export const fetchDirectoryStats = async (surveyId: number): Promise<DirectoryStats> => {
  const params = new URLSearchParams({ survey_id: surveyId.toString() });
  const url = `${DJANGO_URL}${API.DIRECTORIES_STATS}?${params.toString()}`;

  const response = await fetch(url, { credentials: 'include' });
  if (!response.ok) {
    throw new Error(`Failed to fetch directory stats: ${response.statusText}`);
  }
  return response.json();
};

/**
 * Fetch directories with optional filters.
 */
export const fetchDirectories = async (
  surveyId: number,
  options: {
    page?: number;
    pageSize?: number;
    sortField?: string;
    sortOrder?: 'asc' | 'desc';
    cluster?: string;
    origin?: string;
    preserveStatus?: string;
    ownerUsername?: string;
    pathPrefix?: string;
    pathContains?: string;
    minDepth?: number;
    maxDepth?: number;
  } = {}
): Promise<DirectoriesResponse> => {
  const params = new URLSearchParams({ survey_id: surveyId.toString() });

  if (options.page) params.append('page', options.page.toString());
  if (options.pageSize) params.append('page_size', options.pageSize.toString());
  if (options.sortField) params.append('sort_field', options.sortField);
  if (options.sortOrder) params.append('sort_order', options.sortOrder);
  if (options.cluster) params.append('cluster', options.cluster);
  if (options.origin) params.append('origin', options.origin);
  if (options.preserveStatus) params.append('preserve_status', options.preserveStatus);
  if (options.ownerUsername) params.append('owner_username', options.ownerUsername);
  if (options.pathPrefix) params.append('path_prefix', options.pathPrefix);
  if (options.pathContains) params.append('path_contains', options.pathContains);
  if (options.minDepth !== undefined) params.append('min_depth', options.minDepth.toString());
  if (options.maxDepth !== undefined) params.append('max_depth', options.maxDepth.toString());

  const url = `${DJANGO_URL}${API.DIRECTORIES}?${params.toString()}`;

  const response = await fetch(url, { credentials: 'include' });
  if (!response.ok) {
    throw new Error(`Failed to fetch directories: ${response.statusText}`);
  }
  return response.json();
};

/**
 * Fetch files within a directory (on-demand Parquet query).
 */
export const fetchDirectoryFiles = async (
  directoryId: number,
  options: {
    page?: number;
    pageSize?: number;
  } = {}
): Promise<DirectoryFilesResponse> => {
  const params = new URLSearchParams();
  if (options.page) params.append('page', options.page.toString());
  if (options.pageSize) params.append('page_size', options.pageSize.toString());

  const queryString = params.toString();
  const suffix = queryString ? `?${queryString}` : '';
  const basePath = API.DIRECTORY_FILES.replace(':directoryId', directoryId.toString());
  const url = `${DJANGO_URL}${basePath}${suffix}`;

  const response = await fetch(url, { credentials: 'include' });
  if (!response.ok) {
    throw new Error(`Failed to fetch directory files: ${response.statusText}`);
  }
  return response.json();
};

/**
 * Update the preservation status of a single directory.
 */
export const updateDirectoryStatus = async (directoryId: number, status: PreserveStatus): Promise<void> => {
  const url = `${DJANGO_URL}${API.DIRECTORIES}/${directoryId}/`;

  const response = await fetch(url, {
    method: 'PATCH',
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ preserve_status: status }),
  });

  if (!response.ok) {
    throw new Error(`Failed to update directory status: ${response.statusText}`);
  }
};

/**
 * Bulk update preservation status for multiple directories.
 */
export const bulkUpdateDirectoryStatus = async (
  directoryIds: number[],
  status: PreserveStatus
): Promise<{ updated: number }> => {
  const url = `${DJANGO_URL}${POST_API.BULK_UPDATE_DIRECTORY_STATUS}`;

  const response = await fetch(url, {
    method: 'POST',
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      directory_ids: directoryIds,
      preserve_status: status,
    }),
  });

  if (!response.ok) {
    throw new Error(`Failed to bulk update directory status: ${response.statusText}`);
  }
  return response.json();
};

/**
 * Fetch filter options for the directory explorer.
 */
export const fetchDirectoryFilterOptions = async (
  surveyId: number
): Promise<{
  clusters: string[];
  origins: string[];
  statuses: string[];
  owners: string[];
}> => {
  const params = new URLSearchParams({ survey_id: surveyId.toString() });
  const url = `${DJANGO_URL}${API.DIRECTORIES_FILTERLIST}?${params.toString()}`;

  const response = await fetch(url, { credentials: 'include' });
  if (!response.ok) {
    throw new Error(`Failed to fetch filter options: ${response.statusText}`);
  }
  return response.json();
};
