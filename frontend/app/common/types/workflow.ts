/**
 * TypeScript types for Workflow and Processor APIs
 */

// ============================================================================
// Processor Types
// ============================================================================

/**
 * Basic processor information returned from list_processors endpoint
 */
export interface Processor {
  name: string;
  display_name: string;
  version: string;
  default_cluster: string;
  allowed_clusters: string[];
}

/**
 * Complete processor schema with metadata
 */
export interface ProcessorSchema {
  success: boolean;
  processor: string;
  display_name: string;
  version: string;
  default_cluster: string;
  allowed_clusters: string[];
  schema: JSONSchema;
}

/**
 * JSON Schema for processor parameters
 */
export interface JSONSchema {
  type: string;
  properties: Record<string, JSONSchemaProperty>;
  required?: string[];
  dependencies?: Record<string, string[] | Record<string, unknown>>;
}

/**
 * Individual parameter schema property
 */
export interface JSONSchemaProperty {
  type: string;
  title: string;
  description?: string;
  minimum?: number;
  maximum?: number;
  minLength?: number;
  maxLength?: number;
  enum?: (string | number)[];
  default?: string | number | boolean;
  // Custom extensions for processor behavior
  'x-bash-var'?: string | string[];
  'x-bash-format'?: string;
  'x-bash-type'?: string;
  'x-bash-skip'?: boolean;
  'x-cli-flag'?: string | null;
  'x-cli-format'?: string | null;
  'x-cli-composite'?: boolean | string[];
  'x-control-flow'?: boolean;
  'x-advanced'?: boolean;
  'x-conditional'?: string;
  'x-conditional-visibility'?: string | { field: string; operator: string; value: string | number | boolean };
  'x-dynamic-options'?:
    | boolean
    | {
        source: string;
        depends_on_session?: boolean;
      };
  // SLURM/compute resource extensions
  'x-slurm-directive'?: string;
  'x-compute-resource'?: boolean;
  'x-parameter-group'?: string;
  'x-hetjob-component'?: number;
}

/**
 * SLURM job options
 */
export interface SlurmOptions {
  partition: string;
  nodes: number;
  ntasks_per_node: number;
  mem: string;
  time: string;
  [key: string]: string | number;
}

// ============================================================================
// Processor-Specific Custom Data Types
// ============================================================================

/**
 * Option for a dropdown field
 */
export interface FieldOption {
  value: string;
  label: string;
  description?: string;
  [key: string]: unknown; // Allow additional metadata
}

/**
 * Dynamic field options returned from processor's get_dynamic_options endpoint
 */
export interface ProcessorDynamicOptions {
  success: boolean;
  options: Record<string, FieldOption[]>;
}

/**
 * Session-specific default parameter values
 */
export interface ProcessorDefaults {
  success: boolean;
  defaults: Record<string, unknown>;
}

/**
 * Validation error for a specific field
 */
export interface ValidationError {
  field: string;
  message: string;
}

/**
 * Parameter validation result
 */
export interface ValidationResult {
  valid: boolean;
  errors: ValidationError[];
}

/**
 * Example parameter set for documentation
 */
export interface ParameterExample {
  title: string;
  description?: string;
  params: Record<string, unknown>;
}

/**
 * Processor metadata for UI display
 */
export interface ProcessorMetadata {
  success: boolean;
  metadata: {
    help_text: string;
    category?: string;
    examples?: ParameterExample[];
    docs_url?: string | null;
    parameter_notes?: Record<string, string>;
    [key: string]: unknown; // Allow processor-specific metadata
  };
}

// ============================================================================
// Execution Types
// ============================================================================

/**
 * Job execution parameters
 */
export interface ExecutionParams {
  processor: string;
  session_id: string;
  run_name: string;
  cluster: string;
  parameters: Record<string, unknown>;
  auth?: {
    username: string;
    password: string;
  };
}

/**
 * Job execution result
 */
export interface ExecutionResult {
  success: boolean;
  job_id?: string;
  script_path?: string;
  status?: string;
  pipe_execution_id?: number;
  error?: string;
}

/**
 * Job execution status
 */
export interface ExecutionStatus {
  success: boolean;
  execution?: {
    id: number;
    status: string;
    job_id: string;
    cluster: string;
    created_at: string;
    started_at?: string;
    completed_at?: string;
    error_message?: string;
    stdout_log?: string;
    stderr_log?: string;
  };
  error?: string;
}

// ============================================================================
// Form State Types
// ============================================================================

/**
 * Workflow launch form state
 */
export interface WorkflowFormState {
  sessionId: string;
  cluster: string;
  parameters: Record<string, unknown>;
  slurmOptions: Partial<SlurmOptions>;
  isSubmitting: boolean;
  validationErrors: ValidationError[];
}

/**
 * Form field configuration
 */
export interface FormFieldConfig {
  name: string;
  schema: JSONSchemaProperty;
  value: unknown;
  onChange: (value: unknown) => void;
  error?: string;
  disabled?: boolean;
  options?: FieldOption[]; // For dropdown/select fields
}

// ============================================================================
// Component Props Types
// ============================================================================

/**
 * Configuration for session/run selection behavior
 * Allows processors to customize how session selection works
 */
export interface SessionSelectionConfig {
  /**
   * Whether this processor requires MSI session selection via SessionRunSelector
   * Default: true (backward compatible with existing processors)
   */
  requiresSessionSelection: boolean;

  /**
   * Custom function to generate run name when session selection is skipped
   * Used for processors that derive run name from other parameters
   * (e.g., Copick Add Object derives from copick_session + copick_run)
   */
  generateRunName?: (parameters: Record<string, unknown>) => string | null;

  /**
   * Custom function to generate session name when session selection is skipped
   * Used for processors that operate on existing projects/sessions
   */
  generateSessionName?: (parameters: Record<string, unknown>) => string | null;

  /**
   * Informational message to show users when SessionRunSelector is hidden
   * Explains why session selection isn't needed for this mode
   */
  hiddenMessage?: string;

  /**
   * Whether to always show Configure Parameters section regardless of session selection
   * Useful for processors with mode-switching UI inside the parameters section
   * Default: false (only show parameters after session is selected)
   */
  alwaysShowParameters?: boolean;
}

/**
 * Props for WorkflowLaunchForm base component
 */
export interface WorkflowLaunchFormProps {
  processor: Processor;
  schema: ProcessorSchema;
  cluster: 'czii' | 'bruno';
  sessionId?: string;
  onSubmit?: (params: ExecutionParams) => Promise<void>;
  // Session selection behavior configuration
  sessionSelectionConfig?: SessionSelectionConfig;
  // Extensibility hooks
  customFields?: Record<string, React.ComponentType<FormFieldConfig>>;
  additionalSections?: React.ReactNode[];
  onBeforeSubmit?: (params: Record<string, unknown>) => Promise<Record<string, unknown>>;
  customValidation?: (params: Record<string, unknown>) => Promise<ValidationError[]>;
}

/**
 * Props for processor-specific form components
 */
export interface ProcessorFormProps {
  sessionId?: string;
  onSubmit?: (params: ExecutionParams) => Promise<void>;
}
