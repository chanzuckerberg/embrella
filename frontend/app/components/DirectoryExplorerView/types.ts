import { FilterConfig } from '@app/common/types/filter';

/**
 * Represents a filesystem survey record from the backend.
 * Field names match the snake_case API response.
 */
export interface FilesystemSurvey {
  id: number;
  cluster: 'czii' | 'bruno';
  base_path: string;
  status: 'pending' | 'submitted' | 'running' | 'processing' | 'completed' | 'failed';
  job_id: string | null;
  total_files: number;
  total_directories: number;
  total_size_bytes: number;
  total_size_display: string;
  submitted_by: string | null;
  submitted_at: string | null;
  completed_at: string | null;
  error_message: string | null;
  created_at: string;
}

/**
 * Represents a linked domain entity from the backend.
 * Used to link a directory to the domain model that generated it.
 */
export interface LinkedEntity {
  type: string;
  id: number;
  app_label: string;
}

/**
 * Represents a directory summary record from the backend.
 * Each record is an aggregate of files within a directory path.
 * Field names match the snake_case API response.
 */
export interface DirectorySummary {
  id: number;
  survey_id: number;
  cluster: 'czii' | 'bruno';
  path: string;
  file_count: number;
  total_size_bytes: number;
  total_size_display: string;
  owner_username: string | null;
  owner_uid: number | null;
  origin: DirectoryOrigin;
  preserve_status: PreserveStatus;
  status_updated_at: string | null;
  status_updated_by: string | null;
  depth: number;
  newest_file_mtime: string | null;
  oldest_file_mtime: string | null;
  linked_entity: LinkedEntity | null;
}

/**
 * Origin classification for directories.
 */
export type DirectoryOrigin = 'app_generated' | 'synced_from_czii' | 'user_created' | 'unknown';

/**
 * Preservation status for directories.
 */
export type PreserveStatus = 'unset' | 'preserve' | 'delete' | 'review';

/**
 * Represents a file within a directory (from on-demand Parquet query).
 * Field names match the snake_case API response.
 */
export interface DirectoryFile {
  path: string;
  filename: string;
  size_bytes: number;
  size_display: string;
  mtime: string | null;
  uid: number;
  mode: string;
  type: 'file' | 'zarr' | 'directory';
}

/**
 * Filter IDs for the directory explorer view.
 */
export enum DirectoryFilterId {
  CLUSTER = 'CLUSTER',
  ORIGIN = 'ORIGIN',
  PRESERVE_STATUS = 'PRESERVE_STATUS',
  OWNER = 'OWNER',
  DEPTH = 'DEPTH',
}

/**
 * Filter categories that map to backend query parameters.
 */
export type DirectoryFilterCategory = 'cluster' | 'origin' | 'preserve_status' | 'owner_username' | 'depth';

/**
 * Filter configuration type for directory explorer.
 */
export type DirectoryFilterConfig = FilterConfig<DirectoryFilterId, DirectoryFilterCategory>;

/**
 * Statistics response from the directories stats endpoint.
 * Field names match the snake_case API response.
 */
export interface DirectoryStats {
  totals: {
    total_size_bytes: number;
    total_size_display: string;
    total_files: number;
    directory_count: number;
  };
  by_origin: Array<{
    origin: DirectoryOrigin;
    total_size_bytes: number;
    total_size_display: string;
    total_files: number;
    directory_count: number;
  }>;
  by_status: Array<{
    preserve_status: PreserveStatus;
    total_size_bytes: number;
    total_size_display: string;
    total_files: number;
    directory_count: number;
  }>;
  by_owner: Array<{
    owner_username: string | null;
    total_size_bytes: number;
    total_size_display: string;
    total_files: number;
    directory_count: number;
  }>;
}

/**
 * Response from the surveys list endpoint.
 */
export interface SurveysResponse {
  surveys: FilesystemSurvey[];
  total_count: number;
  total_pages: number;
  current_page: number;
}

/**
 * Response from the directories list endpoint.
 */
export interface DirectoriesResponse {
  directories: DirectorySummary[];
  total_count: number;
  total_pages: number;
  current_page: number;
}

/**
 * Response from the directory files endpoint.
 */
export interface DirectoryFilesResponse {
  files: DirectoryFile[];
  directory?: {
    id: number;
    path: string;
    file_count: number;
    total_size_bytes: number;
    total_size_display: string;
  };
  survey_id: number;
  total_count: number;
  total_pages: number;
  current_page: number;
}

/**
 * Color mapping for origin badges.
 */
export const ORIGIN_COLORS: Record<DirectoryOrigin, string> = {
  user_created: '#6E4FF9', // Primary purple
  app_generated: '#9c27b0', // Secondary purple
  synced_from_czii: '#4caf50', // Green
  unknown: '#9e9e9e', // Gray
};

/**
 * Human-readable labels for origin types.
 */
export const ORIGIN_LABELS: Record<DirectoryOrigin, string> = {
  app_generated: 'App Generated',
  synced_from_czii: 'Synced from CZII',
  user_created: 'User Created',
  unknown: 'Unknown',
};

/**
 * Human-readable labels for preserve status.
 */
export const STATUS_LABELS: Record<PreserveStatus, string> = {
  unset: 'Unset',
  preserve: 'Preserve',
  delete: 'Delete',
  review: 'Review',
};

/**
 * Regular expression to match "run###" pattern (e.g., run001, run002, run123).
 */
const RUN_PATTERN = /run\d{3}/i;

/**
 * Check if a directory path contains a "run###" pattern, making it actionable
 * for preservation/deletion marking.
 */
export const isActionablePath = (path: string): boolean => {
  return RUN_PATTERN.test(path);
};
