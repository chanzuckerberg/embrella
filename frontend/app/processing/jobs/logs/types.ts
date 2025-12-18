import type { Job, JobStatus, JobFilterId, JobFilterCategory, JobFilterConfig, JobLog } from '../monitor/types';

// Historical job with additional computed fields
// Note: processor, session, duration, completedAt, hasLogs are now defined in Job base type
// This interface only adds type narrowing for historical job context
export interface HistoricalJob extends Job {
  // Override optional fields to be required for historical jobs
  duration: string;
  completedAt: string;
  processor: string;
  session: string;
  hasLogs: boolean;
}

// Re-export for convenience
export type { Job, JobStatus, JobFilterId, JobFilterCategory, JobFilterConfig, JobLog };
