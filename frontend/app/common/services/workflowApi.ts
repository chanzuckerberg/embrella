/**
 * API service functions for Workflow and Processor operations
 */

import { API, DJANGO_URL, POST_API } from '../constants/api';
import { fetchResource, postResource } from '../queries/fetchResource';
import type {
  ExecutionParams,
  ExecutionResult,
  ExecutionStatus,
  Processor,
  ProcessorDefaults,
  ProcessorDynamicOptions,
  ProcessorMetadata,
  ProcessorSchema,
  ValidationResult,
} from '../types/workflow';

/**
 * Helper to replace URL parameters
 */
function replaceUrlParams(url: string, params: Record<string, string | number>): string {
  let result = url;
  for (const [key, value] of Object.entries(params)) {
    result = result.replace(`:${key}`, String(value));
  }
  return result;
}

/**
 * Helper to build query string
 */
function buildQueryString(params: Record<string, string | number>): string {
  const searchParams = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    searchParams.append(key, String(value));
  }
  const queryString = searchParams.toString();
  return queryString ? `?${queryString}` : '';
}

// ============================================================================
// Processor Discovery
// ============================================================================

/**
 * List all available processors
 */
export async function listProcessors(): Promise<Processor[]> {
  const response = await fetchResource(`${DJANGO_URL}${API.PROCESSORS}`);

  if (!response.ok) {
    throw new Error(`Failed to list processors: ${response.statusText}`);
  }

  const data = await response.json();
  if (!data.success) {
    throw new Error(data.error || 'Failed to list processors');
  }

  return data.processors;
}

/**
 * Get parameter schema for a specific processor
 */
export async function fetchProcessorSchema(processorName: string): Promise<ProcessorSchema> {
  const url = replaceUrlParams(API.PROCESSOR_SCHEMA, { processorName });
  const response = await fetchResource(`${DJANGO_URL}${url}`);

  if (!response.ok) {
    throw new Error(`Failed to fetch processor schema: ${response.statusText}`);
  }

  const data = await response.json();
  if (!data.success) {
    throw new Error(data.error || 'Failed to fetch processor schema');
  }

  return data;
}

// ============================================================================
// Processor-Specific Custom Data
// ============================================================================

/**
 * Get dynamic form field options for a processor
 */
export async function fetchProcessorOptions(
  processorName: string,
  sessionId?: string,
  additionalParams?: Record<string, string | number>
): Promise<ProcessorDynamicOptions> {
  const url = replaceUrlParams(API.PROCESSOR_OPTIONS, { processorName });
  const allParams: Record<string, string | number> = {};
  if (sessionId) {
    allParams.session_id = sessionId;
  }
  if (additionalParams) {
    Object.assign(allParams, additionalParams);
  }
  const queryString = Object.keys(allParams).length > 0 ? buildQueryString(allParams) : '';
  const response = await fetchResource(`${DJANGO_URL}${url}${queryString}`);

  if (!response.ok) {
    throw new Error(`Failed to fetch processor options: ${response.statusText}`);
  }

  const data = await response.json();
  if (!data.success) {
    throw new Error(data.error || 'Failed to fetch processor options');
  }

  return data;
}

/**
 * Validate processor parameters before submission
 */
export async function validateProcessorParams(
  processorName: string,
  parameters: Record<string, unknown>
): Promise<ValidationResult> {
  const url = replaceUrlParams(POST_API.PROCESSOR_VALIDATE, { processorName });
  const response = await postResource(`${DJANGO_URL}${url}`, parameters);

  if (!response.ok) {
    // Even if HTTP error, try to parse validation errors
    try {
      const data = await response.json();
      return data as ValidationResult;
    } catch {
      throw new Error(`Failed to validate parameters: ${response.statusText}`);
    }
  }

  return await response.json();
}

/**
 * Get session-specific default parameters for a processor
 */
export async function fetchProcessorDefaults(processorName: string, sessionId?: string): Promise<ProcessorDefaults> {
  const url = replaceUrlParams(API.PROCESSOR_DEFAULTS, { processorName });
  const queryString = sessionId ? buildQueryString({ session_id: sessionId }) : '';
  const response = await fetchResource(`${DJANGO_URL}${url}${queryString}`);

  if (!response.ok) {
    throw new Error(`Failed to fetch processor defaults: ${response.statusText}`);
  }

  const data = await response.json();
  if (!data.success) {
    throw new Error(data.error || 'Failed to fetch processor defaults');
  }

  return data;
}

/**
 * Get processor metadata (help text, examples, documentation)
 */
export async function fetchProcessorMetadata(processorName: string): Promise<ProcessorMetadata> {
  const url = replaceUrlParams(API.PROCESSOR_METADATA, { processorName });
  const response = await fetchResource(`${DJANGO_URL}${url}`);

  if (!response.ok) {
    throw new Error(`Failed to fetch processor metadata: ${response.statusText}`);
  }

  const data = await response.json();
  if (!data.success) {
    throw new Error(data.error || 'Failed to fetch processor metadata');
  }

  return data;
}

// ============================================================================
// Job Execution
// ============================================================================

/**
 * Execute a processing pipeline
 */
export async function executeWorkflow(params: ExecutionParams): Promise<ExecutionResult> {
  const response = await postResource(
    `${DJANGO_URL}${API.PIPELINE_EXECUTE}`,
    params as unknown as Record<string, unknown>
  );

  if (!response.ok) {
    const errorData = await response.json();

    // Check for SSH setup requirement (403 with ssh_setup_required flag)
    if (response.status === 403 && errorData.ssh_setup_required) {
      // Create a structured error that includes response data for SSH modal
      const error = new Error(errorData.error || 'SSH key not set up') as Error & {
        response: { status: number; data: typeof errorData };
      };
      error.response = {
        status: 403,
        data: errorData,
      };
      throw error;
    }

    // Create a structured error that includes validation errors if present
    const error = new Error(errorData.error || `Failed to execute workflow: ${response.statusText}`) as Error & {
      validation_errors?: string[];
    };
    if (errorData.validation_errors) {
      error.validation_errors = errorData.validation_errors;
    }
    throw error;
  }

  const data = await response.json();
  if (!data.success) {
    // Create a structured error that includes validation errors if present
    const error = new Error(data.error || 'Failed to execute workflow') as Error & {
      validation_errors?: string[];
    };
    if (data.validation_errors) {
      error.validation_errors = data.validation_errors;
    }
    throw error;
  }

  return data;
}

/**
 * Preview rendered SLURM script without submitting
 */
export async function previewWorkflowScript(params: ExecutionParams): Promise<{ script_content: string }> {
  const response = await postResource(
    `${DJANGO_URL}${API.PIPELINE_PREVIEW}`,
    params as unknown as Record<string, unknown>
  );

  if (!response.ok) {
    const errorData = await response.json();

    // Create a structured error that includes validation errors if present
    const error = new Error(errorData.error || `Failed to preview script: ${response.statusText}`) as Error & {
      validation_errors?: string[];
    };
    if (errorData.validation_errors) {
      error.validation_errors = errorData.validation_errors;
    }
    throw error;
  }

  const data = await response.json();
  if (!data.success) {
    // Create a structured error that includes validation errors if present
    const error = new Error(data.error || 'Failed to preview script') as Error & {
      validation_errors?: string[];
    };
    if (data.validation_errors) {
      error.validation_errors = data.validation_errors;
    }
    throw error;
  }

  return { script_content: data.script_content };
}

/**
 * Get execution status by execution ID
 */
export async function fetchExecutionStatus(executionId: number): Promise<ExecutionStatus> {
  const url = replaceUrlParams(API.PIPELINE_EXECUTION_STATUS, { executionId });
  const response = await fetchResource(`${DJANGO_URL}${url}`);

  if (!response.ok) {
    throw new Error(`Failed to fetch execution status: ${response.statusText}`);
  }

  const data = await response.json();
  if (!data.success) {
    throw new Error(data.error || 'Failed to fetch execution status');
  }

  return data;
}

/**
 * Get execution status by job ID
 */
export async function fetchExecutionByJobId(jobId: string): Promise<ExecutionStatus> {
  const url = replaceUrlParams(API.PIPELINE_EXECUTION_BY_JOB_ID, { jobId });
  const response = await fetchResource(`${DJANGO_URL}${url}`);

  if (!response.ok) {
    throw new Error(`Failed to fetch execution by job ID: ${response.statusText}`);
  }

  const data = await response.json();
  if (!data.success) {
    throw new Error(data.error || 'Failed to fetch execution by job ID');
  }

  return data;
}

// ============================================================================
// Copick-Specific Endpoints
// ============================================================================

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
