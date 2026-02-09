/**
 * API service functions for Membraneseg-specific operations
 */

import { API, DJANGO_URL } from '@app/common/constants/api';
import { fetchResource } from '@app/common/queries/fetchResource';
import { buildQueryString } from '@app/common/services/workflowApi';

interface MembranesegRunsResult {
  success: boolean;
  run_numbers: string[];
  next_run_name: string;
}

/**
 * Calculate the next run name from a list of run numbers.
 * Run numbers are returned without 'run' prefix (e.g., ['001', '002']).
 */
function calculateNextRunName(runNumbers: string[]): string {
  let nextRunNum = 1;
  if (runNumbers.length > 0) {
    const maxNum = Math.max(...runNumbers.map((n: string) => parseInt(n, 10) || 0));
    nextRunNum = maxNum + 1;
  }
  return `run${String(nextRunNum).padStart(3, '0')}`;
}

/**
 * Get existing Membraneseg ProcRuns from the database for a given session.
 * Uses the shared copick_params endpoint with plan_type=membraneseg.
 * Numbering is per-session (run001, run002, etc.)
 */
export async function fetchMembranesegRuns(sessionId: string): Promise<MembranesegRunsResult> {
  const queryString = buildQueryString({
    session_name: sessionId,
    plan_type: 'membraneseg',
  });
  // Uses shared copick-ecosystem endpoint for plan run lookups
  // TODO: refactor API name, COPICK add object is used by all copick-specific projects
  const response = await fetchResource(`${DJANGO_URL}${API.COPICK_ADD_OBJECT_PARAMS}${queryString}`);

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
