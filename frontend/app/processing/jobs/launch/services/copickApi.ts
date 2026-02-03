/**
 * API service functions for Copick-specific operations
 */

import { API, DJANGO_URL } from '@app/common/constants/api';
import { fetchResource } from '@app/common/queries/fetchResource';
import { buildQueryString } from '@app/common/services/workflowApi';

/**
 * Get available template maps for Copick objects
 */
export async function fetchCopickTemplateMaps(): Promise<{
  success: boolean;
  template_maps: Array<{
    name: string;
    label: string;
    diameter: number;
    pdb_id: string;
    map_file: string;
    voxel_size: number;
    description: string;
  }>;
}> {
  const response = await fetchResource(`${DJANGO_URL}${API.COPICK_TEMPLATE_MAPS}`);

  if (!response.ok) {
    throw new Error(`Failed to fetch copick template maps: ${response.statusText}`);
  }

  const data = await response.json();
  if (!data.success) {
    throw new Error(data.error || 'Failed to fetch copick template maps');
  }

  return data;
}

interface CopickRunsResult {
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
 * Fetch Copick ProcRuns from the database for a given plan type.
 * Common helper for copick-add-object, copick-import, etc.
 */
async function fetchCopickPlanRuns(sessionId: string, planType: string): Promise<CopickRunsResult> {
  const queryString = buildQueryString({
    session_name: sessionId,
    plan_type: planType,
  });
  const response = await fetchResource(`${DJANGO_URL}${API.COPICK_ADD_OBJECT_PARAMS}${queryString}`);

  if (!response.ok) {
    throw new Error(`Failed to fetch ${planType} runs: ${response.statusText}`);
  }

  const data = await response.json();
  if (data.error) {
    throw new Error(data.error || `Failed to fetch ${planType} runs`);
  }

  const sessionData = data.sessions?.[0];
  const runNumbers = sessionData?.run_numbers || [];

  return {
    success: true,
    run_numbers: runNumbers,
    next_run_name: calculateNextRunName(runNumbers),
  };
}

/**
 * Get existing Copick add_object ProcRuns from the database.
 * Uses the copick_params endpoint with plan_type=copick-add-object.
 * Numbering is per-session (run001, run002, etc.)
 */
export function fetchCopickObjectRuns(sessionId: string): Promise<CopickRunsResult> {
  return fetchCopickPlanRuns(sessionId, 'copick-add-object');
}

/**
 * Get existing Copick import ProcRuns from the database.
 * Uses the copick_params endpoint with plan_type=copick-import.
 * Numbering is per-session (run001, run002, etc.)
 */
export function fetchCopickImportRuns(sessionId: string): Promise<CopickRunsResult> {
  return fetchCopickPlanRuns(sessionId, 'copick-import');
}

/**
 * Get available Copick runs for a given session
 */
export async function fetchCopickRuns(sessionId: string): Promise<{
  success: boolean;
  copick_runs: Array<{
    name: string;
    label: string;
    description: string;
  }>;
}> {
  const queryString = buildQueryString({ session_id: sessionId });
  const response = await fetchResource(`${DJANGO_URL}${API.COPICK_RUNS}${queryString}`);

  if (!response.ok) {
    throw new Error(`Failed to fetch copick runs: ${response.statusText}`);
  }

  const data = await response.json();
  if (!data.success) {
    throw new Error(data.error || 'Failed to fetch copick runs');
  }

  return data;
}
