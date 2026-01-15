import { EntityLinkField } from '@app/common/types/entity';
import { FilterConfig } from '@app/common/types/filter';

// Job data structure from backend API
export interface Job {
  job: EntityLinkField;
  jobName: string;
  user: string;
  status: JobStatus;
  timeUsed: string;
  timeLeft: string;
  nodes: string;
  partition: string;
  nodeList: string;
  cluster: 'czii' | 'bruno';
  submittedAt: string | null;
  parameters: Record<string, unknown> | null;
  errorMessage: string | null;
  isWorkflowLaunched: boolean;
  // Historical job fields (for completed jobs)
  processor?: string;
  session?: string;
  duration?: string;
  completedAt?: string;
  hasLogs?: boolean;
  // Syncer status (if available)
  syncerStatus?: SyncerStatus;
}

// Job status (human-readable labels)
export type JobStatus = 'Running' | 'Pending' | 'Completing' | 'Completed' | 'Failed' | 'Cancelled' | 'Timeout';

// Human-readable job status labels (now same as keys)
export const JOB_STATUS_LABELS: Record<JobStatus, string> = {
  Running: 'Running',
  Pending: 'Pending',
  Completing: 'Completing',
  Completed: 'Completed',
  Failed: 'Failed',
  Cancelled: 'Cancelled',
  Timeout: 'Timeout',
};

// Color coding for job statuses
export const JOB_STATUS_COLORS: Record<JobStatus, string> = {
  Running: '#6E4FF9', // Purple
  Pending: '#ff9800', // Orange
  Completing: '#9c27b0', // Purple
  Completed: '#4caf50', // Green
  Failed: '#f44336', // Red
  Cancelled: '#9e9e9e', // Gray
  Timeout: '#ff5722', // Deep Orange
};

// Filter IDs for job management
export enum JobFilterId {
  JOB_ID = 'JOB_ID',
  USER = 'USER',
  STATUS = 'STATUS',
  CLUSTER = 'CLUSTER',
  JOB_NAME = 'JOB_NAME',
  PARTITION = 'PARTITION',
  COMPLETED_DATE_RANGE = 'COMPLETED_DATE_RANGE',
}

// Filter categories
export type JobFilterCategory =
  | 'jobId'
  | 'user'
  | 'status'
  | 'cluster'
  | 'jobName'
  | 'partition'
  | 'completedDateRange';

// Filter configuration type
export type JobFilterConfig = FilterConfig<JobFilterId, JobFilterCategory>;

// Job Log from backend (historical data)
export interface JobLog {
  user_id: number;
  job_name: string;
  advanced: boolean;
  job_id: string;
  created_at: string;
  parameters: Record<string, unknown>;
  error_message: string | null;
  script_content?: string | null;
  // SLURM job execution logs
  stdout_log?: string | null;
  stderr_log?: string | null;
  logs_fetched_at?: string | null;
  log_fetch_error?: string | null;
}

// Response from jobs list endpoint
export interface JobsResponse {
  jobs: Job[];
  total: number;
  cluster: 'czii' | 'bruno';
}

// Response from bulk cancel endpoint
export interface BulkCancelResponse {
  success: boolean;
  cancelled: number;
  failed: number;
  results: Array<{
    job_id: string;
    success: boolean;
    message: string;
  }>;
}

// Syncer log entry
export interface SyncerLogEntry {
  timestamp: string;
  action_type:
    | 'init'
    | 'sync_start'
    | 'sync_complete'
    | 'file_found'
    | 'tomogram_created'
    | 'tomogram_deleted'
    | 'review_updated'
    | 'job_check'
    | 'error'
    | 'warning'
    | 'stopped';
  message: string;
  metadata: Record<string, unknown>;
}

// Syncer process status
export interface SyncerStatus {
  status: 'running' | 'stopped' | 'completed' | 'failed' | null;
  last_heartbeat: string | null;
  can_rerun: boolean;
  syncer_type: string | null;
}

// Response from syncer logs endpoint
export interface SyncerLogsResponse {
  success: boolean;
  logs: SyncerLogEntry[];
  syncer_status: SyncerStatus | null;
}

// Response from syncer rerun endpoint
export interface SyncerRerunResponse {
  success: boolean;
  message?: string;
  error?: string;
}
