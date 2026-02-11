/**
 * API service functions for Membraneseg-specific operations
 */

import { API, DJANGO_URL } from '@app/common/constants/api';
import { fetchResource } from '@app/common/queries/fetchResource';
import { buildQueryString } from '@app/common/services/workflowApi';
import { calculateNextRunName } from '../utils/runNumbers';

interface MembranesegRunsResult {
  success: boolean;
  run_numbers: string[];
  next_run_name: string;
}

/**
 * Get existing Membraneseg ProcRuns from the database for a given session.
 * Uses the plan_runs endpoint with plan_type=membraneseg.
 * Numbering is per-session (run001, run002, etc.)
 */
export async function fetchMembranesegRuns(sessionId: string): Promise<MembranesegRunsResult> {
  const queryString = buildQueryString({
    session_name: sessionId,
    plan_type: 'membraneseg',
  });
  const response = await fetchResource(`${DJANGO_URL}${API.PLAN_RUNS}${queryString}`);

  if (!response.ok) {
    throw new Error(`Failed to fetch membraneseg runs: ${response.statusText}`);
  }

  const data = await response.json();
  if (data.error) {
    throw new Error(data.error || 'Failed to fetch membraneseg runs');
  }

  const sessionData = data.sessions?.[0];
  const runNumbers = sessionData?.run_numbers || [];

  return {
    success: true,
    run_numbers: runNumbers,
    next_run_name: calculateNextRunName(runNumbers),
  };
}
