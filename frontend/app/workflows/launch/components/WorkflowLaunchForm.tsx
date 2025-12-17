'use client';

/**
 * WorkflowLaunchForm - Enhanced base component for processor workflow launch
 *
 * Features:
 * - Numbered step-by-step flow
 * - SessionRunSelector integration
 * - Dependency checking
 * - Pre-submission validation
 * - SSH setup handling
 * - Dynamic field options
 * - Custom validation hooks
 */

import {
  Accordion,
  AccordionDetails,
  AccordionSummary,
  Alert,
  Box,
  Button,
  CircularProgress,
  FormControl,
  FormControlLabel,
  FormHelperText,
  Grid,
  InputLabel,
  MenuItem,
  Select,
  Switch,
  TextField,
  Typography,
} from '@mui/material';
import { useEffect, useMemo, useState } from 'react';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import VisibilityIcon from '@mui/icons-material/Visibility';
import type {
  ExecutionParams,
  FieldOption,
  ProcessorSchema,
  ValidationError,
  WorkflowLaunchFormProps,
} from '@app/common/types/workflow';
import {
  executeWorkflow,
  fetchProcessorDefaults,
  fetchProcessorMetadata,
  fetchProcessorOptions,
  previewWorkflowScript,
  validateProcessorParams,
} from '@app/common/services/workflowApi';
import { SessionRunSelector, SessionRunSelection } from './SessionRunSelector';
import { DependencyChecker } from './DependencyChecker';
import ScriptPreviewModal from './ScriptPreviewModal';
import { SSHSetupModal } from '@app/common/components/SSHSetupModal';
import { API, DJANGO_URL } from '@app/common/constants/api';
import { fetchResource } from '@app/common/queries/fetchResource';

export default function WorkflowLaunchForm({
  processor,
  schema,
  cluster,
  sessionId: initialSessionId,
  onSubmit,
  sessionSelectionConfig = { requiresSessionSelection: true }, // Default: requires session selection
  customFields,
  additionalSections,
  onBeforeSubmit,
  customValidation,
}: WorkflowLaunchFormProps) {
  // Form state
  const [sessionRunSelection, setSessionRunSelection] = useState<SessionRunSelection>({
    sessionName: null,
    runName: null,
    isValid: !sessionSelectionConfig.requiresSessionSelection, // Valid by default if session selection not required
  });
  const [parameters, setParameters] = useState<Record<string, any>>({});
  const [slurmOptions, setSlurmOptions] = useState<Record<string, any>>(() => {
    // Initialize SLURM options from schema field defaults
    const defaults: Record<string, any> = {};
    for (const [fieldName, fieldSchema] of Object.entries(schema.schema.properties)) {
      // Only include fields with x-slurm-directive or x-compute-resource
      if (fieldSchema['x-slurm-directive'] || fieldSchema['x-compute-resource']) {
        if (fieldSchema.default !== undefined) {
          defaults[fieldName] = fieldSchema.default;
        }
      }
    }
    return defaults;
  });

  // Loading states
  const [isLoadingDefaults, setIsLoadingDefaults] = useState(false);
  const [isLoadingOptions, setIsLoadingOptions] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Data states
  const [dynamicOptions, setDynamicOptions] = useState<Record<string, FieldOption[]>>({});
  const [metadata, setMetadata] = useState<any>(null);
  const [lookedUpIds, setLookedUpIds] = useState<{ pipe_in_plan_id: number; proc_run_id: number } | null>(null);
  const [dependenciesMet, setDependenciesMet] = useState<boolean>(true);

  // Validation
  const [validationErrors, setValidationErrors] = useState<ValidationError[]>([]);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [submitSuccess, setSubmitSuccess] = useState(false);
  const [executionResult, setExecutionResult] = useState<any>(null);

  // SSH setup
  const [sshModalOpen, setSshModalOpen] = useState(false);
  const [sshCluster, setSshCluster] = useState<'czii' | 'bruno'>('czii');
  const [currentUser, setCurrentUser] = useState<{ username: string } | null>(null);

  // Script preview
  const [previewModalOpen, setPreviewModalOpen] = useState(false);
  const [previewScript, setPreviewScript] = useState<string | null>(null);
  const [isLoadingPreview, setIsLoadingPreview] = useState(false);
  const [previewError, setPreviewError] = useState<string | null>(null);

  // Derived session/run info - either from SessionRunSelector or generated from parameters
  const effectiveSessionName = useMemo(() => {
    if (sessionSelectionConfig.requiresSessionSelection) {
      return sessionRunSelection.sessionName;
    }
    // Generate from parameters if custom function provided
    return sessionSelectionConfig.generateSessionName?.(parameters) || null;
  }, [sessionSelectionConfig, sessionRunSelection.sessionName, parameters]);

  const effectiveRunName = useMemo(() => {
    if (sessionSelectionConfig.requiresSessionSelection) {
      return sessionRunSelection.runName;
    }
    // Generate from parameters if custom function provided
    return sessionSelectionConfig.generateRunName?.(parameters) || null;
  }, [sessionSelectionConfig, sessionRunSelection.runName, parameters]);

  // Fetch current user on mount
  useEffect(() => {
    const fetchUser = async () => {
      try {
        const response = await fetchResource(`${DJANGO_URL}/user`);
        // fetchResource handles 401 redirects automatically
        if (response.ok) {
          const data = await response.json();
          setCurrentUser(data);
        }
      } catch (error) {
        console.error('Failed to fetch user:', error);
      }
    };
    fetchUser();
  }, []);

  // Load processor metadata on mount
  useEffect(() => {
    const loadMetadata = async () => {
      try {
        const result = await fetchProcessorMetadata(processor.name);
        setMetadata(result.metadata);
      } catch (error) {
        console.error('Failed to load processor metadata:', error);
      }
    };
    loadMetadata();
  }, [processor.name]);

  // Look up IDs when session/run selection is complete
  useEffect(() => {
    const lookupIds = async () => {
      // Skip lookup if session selection not required
      if (!sessionSelectionConfig.requiresSessionSelection) {
        setLookedUpIds(null);
        setDependenciesMet(true); // No dependencies to check
        return;
      }

      if (!sessionRunSelection.sessionName || !sessionRunSelection.runName) {
        setLookedUpIds(null);
        return;
      }

      try {
        const lookupUrl = `${DJANGO_URL}${API.PIPELINE_LOOKUP_IDS}?session_name=${encodeURIComponent(
          sessionRunSelection.sessionName
        )}&run_name=${encodeURIComponent(sessionRunSelection.runName)}&processor_name=${encodeURIComponent(
          processor.name
        )}`;

        const lookupResponse = await fetch(lookupUrl, { credentials: 'include' });

        if (lookupResponse.ok) {
          const lookupData = await lookupResponse.json();
          if (lookupData.success) {
            setLookedUpIds({
              pipe_in_plan_id: lookupData.pipe_in_plan_id,
              proc_run_id: lookupData.proc_run_id,
            });
          }
        } else if (lookupResponse.status === 404) {
          // Run doesn't exist yet - this is okay for new runs
          // Set null to indicate no existing run (skip dependency check)
          setLookedUpIds(null);
          // For new runs, automatically assume dependencies are met (no prior runs to check)
          setDependenciesMet(true);
        }
      } catch (err) {
        console.error('Error looking up IDs:', err);
      }
    };

    lookupIds();
  }, [
    sessionRunSelection.sessionName,
    sessionRunSelection.runName,
    processor.name,
    sessionSelectionConfig.requiresSessionSelection,
  ]);

  // Load initial options for Copick (even without session selected)
  useEffect(() => {
    if (processor.name !== 'copick') return;

    const loadInitialOptions = async () => {
      try {
        setIsLoadingOptions(true);
        // Fetch options without session_id to get copick_session options
        const optionsResult = await fetchProcessorOptions(processor.name, undefined, undefined);
        setDynamicOptions(optionsResult.options);
        setIsLoadingOptions(false);
      } catch (error) {
        console.error('Failed to load initial options:', error);
        setIsLoadingOptions(false);
      }
    };

    loadInitialOptions();
  }, [processor.name]);

  // Load defaults and options when session changes
  useEffect(() => {
    if (!sessionRunSelection.sessionName) return;

    const loadSessionData = async () => {
      try {
        // Load defaults
        setIsLoadingDefaults(true);
        const defaultsResult = await fetchProcessorDefaults(processor.name, sessionRunSelection.sessionName);
        setParameters((prev) => ({
          ...defaultsResult.defaults,
          ...prev, // Keep any user changes
        }));
        setIsLoadingDefaults(false);

        // Load dynamic options
        setIsLoadingOptions(true);
        // Pass current parameter values that affect dynamic options (e.g., import_tomo_type for Copick)
        const additionalParams: Record<string, string | number> = {};
        if (parameters.import_tomo_type) {
          additionalParams.import_tomo_type = parameters.import_tomo_type;
        }
        const optionsResult = await fetchProcessorOptions(
          processor.name,
          sessionRunSelection.sessionName,
          Object.keys(additionalParams).length > 0 ? additionalParams : undefined
        );
        setDynamicOptions(optionsResult.options);

        // Set default values for dynamic option fields (first option) if not already set
        const newDefaults: Record<string, string | number | boolean> = {};
        for (const [fieldName, fieldOptions] of Object.entries(optionsResult.options)) {
          const options = fieldOptions as FieldOption[];
          if (options.length > 0 && !parameters[fieldName]) {
            newDefaults[fieldName] = options[0].value;
          }
        }
        if (Object.keys(newDefaults).length > 0) {
          setParameters((prev) => ({
            ...prev,
            ...newDefaults,
          }));
        }

        setIsLoadingOptions(false);
      } catch (error) {
        console.error('Failed to load session data:', error);
        setIsLoadingDefaults(false);
        setIsLoadingOptions(false);
      }
    };

    loadSessionData();
  }, [sessionRunSelection.sessionName, processor.name]);

  // Refetch dynamic options when import_tomo_type changes (Copick processor)
  useEffect(() => {
    // Only refetch if we have a session and this is the Copick processor
    if (!sessionRunSelection.sessionName || processor.name !== 'copick') return;

    // Skip if import_tomo_type is not set yet (will be handled by session load)
    if (!parameters.import_tomo_type) return;

    const refetchOptions = async () => {
      try {
        setIsLoadingOptions(true);
        const optionsResult = await fetchProcessorOptions(processor.name, sessionRunSelection.sessionName, {
          import_tomo_type: parameters.import_tomo_type,
        });
        setDynamicOptions(optionsResult.options);
        setIsLoadingOptions(false);
      } catch (error) {
        console.error('Failed to refetch options:', error);
        setIsLoadingOptions(false);
      }
    };

    refetchOptions();
  }, [parameters.import_tomo_type, sessionRunSelection.sessionName, processor.name]);

  // Refetch dynamic options when copick_session changes (Copick processor add_object)
  useEffect(() => {
    // Only refetch if we have copick_session and this is the Copick processor
    if (processor.name !== 'copick') return;
    if (!parameters.copick_session) return;

    const refetchOptions = async () => {
      try {
        setIsLoadingOptions(true);
        const optionsResult = await fetchProcessorOptions(
          processor.name,
          undefined, // No session_id for add_object operation
          { copick_session: parameters.copick_session }
        );
        // Merge with existing options (don't overwrite copick_session)
        setDynamicOptions((prev) => ({
          ...prev,
          ...optionsResult.options,
        }));
        setIsLoadingOptions(false);
      } catch (error) {
        console.error('Failed to refetch options:', error);
        setIsLoadingOptions(false);
      }
    };

    refetchOptions();
  }, [parameters.copick_session, processor.name]);

  // Load initial options for Membraneseg (even without session selected)
  useEffect(() => {
    if (processor.name !== 'membraneseg') return;

    const loadInitialOptions = async () => {
      try {
        setIsLoadingOptions(true);
        // Fetch options without session_id to get copick_session options
        const optionsResult = await fetchProcessorOptions(processor.name, undefined, undefined);
        setDynamicOptions(optionsResult.options);

        // Auto-select first copick_session if available
        if (optionsResult.options.copick_session?.length > 0 && !parameters.copick_session) {
          setParameters((prev) => ({
            ...prev,
            copick_session: optionsResult.options.copick_session[0].value,
          }));
        }

        setIsLoadingOptions(false);
      } catch (error) {
        console.error('Failed to load initial membraneseg options:', error);
        setIsLoadingOptions(false);
      }
    };

    loadInitialOptions();
  }, [processor.name]);

  // Refetch membraneseg options when copick_session changes
  useEffect(() => {
    if (processor.name !== 'membraneseg') return;
    if (!parameters.copick_session) return;

    const refetchOptions = async () => {
      try {
        setIsLoadingOptions(true);
        const optionsResult = await fetchProcessorOptions(processor.name, undefined, {
          copick_session: parameters.copick_session,
        });
        // Merge with existing options
        setDynamicOptions((prev) => ({
          ...prev,
          ...optionsResult.options,
        }));

        // Auto-select first copick_procrun if available
        if (optionsResult.options.copick_procrun?.length > 0 && !parameters.copick_procrun) {
          setParameters((prev) => ({
            ...prev,
            copick_procrun: optionsResult.options.copick_procrun[0].value,
          }));
        }

        setIsLoadingOptions(false);
      } catch (error) {
        console.error('Failed to refetch membraneseg options:', error);
        setIsLoadingOptions(false);
      }
    };

    refetchOptions();
  }, [parameters.copick_session, processor.name]);

  // Refetch membraneseg tomo options when copick_procrun changes
  useEffect(() => {
    if (processor.name !== 'membraneseg') return;
    if (!parameters.copick_session || !parameters.copick_procrun) return;

    const refetchTomoOptions = async () => {
      try {
        setIsLoadingOptions(true);
        const optionsResult = await fetchProcessorOptions(processor.name, undefined, {
          copick_session: parameters.copick_session,
          copick_procrun: parameters.copick_procrun,
        });
        // Merge with existing options
        setDynamicOptions((prev) => ({
          ...prev,
          ...optionsResult.options,
        }));

        // Auto-select first tomo_type if available
        if (optionsResult.options.tomo_type?.length > 0 && !parameters.tomo_type) {
          setParameters((prev) => ({
            ...prev,
            tomo_type: optionsResult.options.tomo_type[0].value,
          }));
        }

        setIsLoadingOptions(false);
      } catch (error) {
        console.error('Failed to refetch membraneseg tomo options:', error);
        setIsLoadingOptions(false);
      }
    };

    refetchTomoOptions();
  }, [parameters.copick_session, parameters.copick_procrun, processor.name]);

  // Refetch membraneseg voxel size options when tomo_type changes
  useEffect(() => {
    if (processor.name !== 'membraneseg') return;
    if (!parameters.copick_session || !parameters.copick_procrun || !parameters.tomo_type) return;

    const refetchVoxelOptions = async () => {
      try {
        setIsLoadingOptions(true);
        const optionsResult = await fetchProcessorOptions(processor.name, undefined, {
          copick_session: parameters.copick_session,
          copick_procrun: parameters.copick_procrun,
          tomo_type: parameters.tomo_type,
        });
        // Merge with existing options
        setDynamicOptions((prev) => ({
          ...prev,
          ...optionsResult.options,
        }));

        // Auto-select first tomo_voxel_size if available
        if (optionsResult.options.tomo_voxel_size?.length > 0 && !parameters.tomo_voxel_size) {
          setParameters((prev) => ({
            ...prev,
            tomo_voxel_size: optionsResult.options.tomo_voxel_size[0].value,
          }));
        }

        setIsLoadingOptions(false);
      } catch (error) {
        console.error('Failed to refetch membraneseg voxel options:', error);
        setIsLoadingOptions(false);
      }
    };

    refetchVoxelOptions();
  }, [parameters.copick_session, parameters.copick_procrun, parameters.tomo_type, processor.name]);

  // Check if all required parameters are filled
  const areRequiredParametersFilled = () => {
    if (!schema.schema.required) return true;
    return schema.schema.required.every((fieldName) => {
      const value = parameters[fieldName];
      return value !== undefined && value !== null && value !== '';
    });
  };

  // Handle parameter change
  const handleParameterChange = (name: string, value: any) => {
    setParameters((prev) => ({ ...prev, [name]: value }));
    // Clear validation error for this field
    setValidationErrors((prev) => prev.filter((e) => e.field !== name));
  };

  const handleSlurmOptionChange = (name: string, value: any) => {
    setSlurmOptions((prev) => ({ ...prev, [name]: value }));
    // Clear validation error for this field
    setValidationErrors((prev) => prev.filter((e) => e.field !== name));
  };

  // Evaluate conditional expressions
  // Supports two formats:
  // 1. String format: "slurm_partition == 'gpu'"
  // 2. Object format (x-conditional-visibility): { field: 'operation', operator: 'eq', value: 'create' }
  const evaluateConditional = (conditional: string | { field: string; operator: string; value: any }): boolean => {
    if (!conditional) return true;

    // Handle structured object format (x-conditional-visibility)
    if (typeof conditional === 'object') {
      const { field, operator, value } = conditional;
      const fieldValue = parameters[field] ?? slurmOptions[field];

      switch (operator) {
        case 'eq':
        case '==':
          return fieldValue === value;
        case 'ne':
        case '!=':
          return fieldValue !== value;
        case 'gt':
        case '>':
          return fieldValue > value;
        case 'lt':
        case '<':
          return fieldValue < value;
        case 'gte':
        case '>=':
          return fieldValue >= value;
        case 'lte':
        case '<=':
          return fieldValue <= value;
        default:
          console.warn(`Unknown conditional operator: ${operator}`);
          return true;
      }
    }

    // Handle simple string format (x-conditional)
    if (typeof conditional === 'string' && conditional.includes('==')) {
      // Check for OR operator (||)
      if (conditional.includes('||')) {
        const orParts = conditional.split('||').map((p) => p.trim());
        // Evaluate each part and return true if ANY are true
        return orParts.some((part) => evaluateConditional(part));
      }

      // Check for AND operator (&&)
      if (conditional.includes('&&')) {
        const andParts = conditional.split('&&').map((p) => p.trim());
        // Evaluate each part and return true only if ALL are true
        return andParts.every((part) => evaluateConditional(part));
      }

      // Simple single condition
      const parts = conditional.split('==').map((p) => p.trim());
      if (parts.length === 2) {
        const fieldName = parts[0];
        const expectedValue = parts[1].replace(/['"]/g, ''); // Remove quotes

        // Check if this is a SLURM field (look in slurmOptions) or regular field (look in parameters)
        const fieldSchema = schema.schema.properties[fieldName];
        const isSlurmField = fieldSchema?.['x-compute-resource'] || fieldSchema?.['x-slurm-directive'];

        // Get actual value from appropriate state, or fall back to schema default
        let actualValue = isSlurmField ? slurmOptions[fieldName] : parameters[fieldName];
        if (actualValue === undefined || actualValue === null || actualValue === '') {
          actualValue = fieldSchema?.default;
        }

        return String(actualValue || '') === expectedValue;
      }
    }

    // Fallback: treat as boolean field reference
    const fieldSchema = schema.schema.properties[conditional];
    const isSlurmField = fieldSchema?.['x-compute-resource'] || fieldSchema?.['x-slurm-directive'];
    const value = isSlurmField ? slurmOptions[conditional] : parameters[conditional];

    if (value === undefined || value === null) {
      return Boolean(fieldSchema?.default);
    }
    return Boolean(value);
  };

  // Handle SSH setup success
  const handleSSHSetupSuccess = () => {
    setSshModalOpen(false);
    // Retry submission
    handleSubmit();
  };

  // Handle script preview
  const handlePreviewScript = async () => {
    setPreviewError(null);
    setPreviewScript(null);

    // Validate session selection (only if required)
    if (sessionSelectionConfig.requiresSessionSelection) {
      if (!sessionRunSelection.isValid) {
        setPreviewError('Please select a valid session and run name');
        setPreviewModalOpen(true);
        return;
      }
    } else {
      // For processors that don't require session selection, check generated names
      if (!effectiveSessionName || !effectiveRunName) {
        setPreviewError('Required parameters not filled for run name generation');
        setPreviewModalOpen(true);
        return;
      }
    }

    if (!dependenciesMet) {
      setPreviewError('Dependencies not met. Please complete required processing steps first.');
      setPreviewModalOpen(true);
      return;
    }

    if (!areRequiredParametersFilled()) {
      setPreviewError('Please fill in all required parameters');
      setPreviewModalOpen(true);
      return;
    }

    try {
      setIsLoadingPreview(true);
      setPreviewModalOpen(true);

      // Apply onBeforeSubmit hook if provided
      let finalParams = { ...parameters };
      if (onBeforeSubmit) {
        finalParams = await onBeforeSubmit(finalParams);
      }

      // Merge SLURM options into parameters (backend extracts SLURM directives from parameters)
      const mergedParams = { ...finalParams, ...slurmOptions };

      // Build execution params (same as submit, but for preview)
      const executionParams: ExecutionParams = {
        processor: processor.name,
        session_id: effectiveSessionName!, // Use effective (either selected or generated)
        run_name: effectiveRunName!, // Use effective (either selected or generated)
        cluster: cluster,
        parameters: mergedParams,
        auth: {
          username: currentUser?.username || '',
          password: '',
        },
      };

      // Get script preview
      const result = await previewWorkflowScript(executionParams);
      setPreviewScript(result.script_content);
    } catch (error: any) {
      console.error('Error previewing script:', error);

      // Build error message including validation errors if present
      let errorMessage = error.message || 'Failed to preview script';
      if (error.validation_errors && error.validation_errors.length > 0) {
        errorMessage += '\n\n' + error.validation_errors.join('\n\n');
      }
      setPreviewError(errorMessage);
    } finally {
      setIsLoadingPreview(false);
    }
  };

  // Handle form submission
  const handleSubmit = async (event?: React.FormEvent) => {
    if (event) event.preventDefault();

    setSubmitError(null);
    setValidationErrors([]);
    setSubmitSuccess(false);

    // Validate session selection (only if required)
    if (sessionSelectionConfig.requiresSessionSelection) {
      if (!sessionRunSelection.isValid) {
        setSubmitError('Please select a valid session and run name');
        return;
      }
    } else {
      // For processors that don't require session selection, check generated names
      if (!effectiveSessionName || !effectiveRunName) {
        setSubmitError('Required parameters not filled for run name generation');
        return;
      }
    }

    // Note: lookedUpIds can be null for new runs, which is okay
    // The backend will create the run on submission

    if (!dependenciesMet) {
      setSubmitError('Dependencies not met. Please complete required processing steps first.');
      return;
    }

    if (!areRequiredParametersFilled()) {
      setSubmitError('Please fill in all required parameters');
      return;
    }

    try {
      setIsSubmitting(true);

      // Apply onBeforeSubmit hook if provided
      let finalParams = { ...parameters };
      if (onBeforeSubmit) {
        finalParams = await onBeforeSubmit(finalParams);
      }

      // Merge SLURM options into parameters (backend extracts SLURM directives from parameters)
      const mergedParams = { ...finalParams, ...slurmOptions };

      // Run custom validation if provided
      if (customValidation) {
        const customErrors = await customValidation(mergedParams);
        if (customErrors.length > 0) {
          setValidationErrors(customErrors);
          setIsSubmitting(false);
          return;
        }
      }

      // Validate parameters with backend
      const validationResult = await validateProcessorParams(processor.name, mergedParams);
      if (!validationResult.valid) {
        setValidationErrors(validationResult.errors);
        setIsSubmitting(false);
        return;
      }

      // Build execution params
      const executionParams: ExecutionParams = {
        processor: processor.name,
        session_id: effectiveSessionName!, // Use effective (either selected or generated)
        run_name: effectiveRunName!, // Use effective (either selected or generated)
        cluster: cluster,
        parameters: mergedParams,
        auth: {
          username: currentUser?.username || '',
          password: '', // Empty for SSH key-based authentication
        },
      };

      // Execute workflow
      const result = await executeWorkflow(executionParams);

      if (result.success) {
        setExecutionResult(result);
        setSubmitSuccess(true);

        // Call onSubmit callback if provided (for custom post-submission handling)
        if (onSubmit) {
          await onSubmit(executionParams);
        }

        // Auto-redirect to monitoring page after success
        setTimeout(() => {
          window.location.href = '/processing/monitor';
        }, 2000);
      }

      setIsSubmitting(false);
    } catch (error: any) {
      console.error('Failed to submit workflow:', error);

      // Check for SSH setup requirement
      if (error.response?.status === 403 && error.response?.data?.ssh_setup_required) {
        console.log('SSH setup required, opening modal:', {
          cluster: error.response.data.cluster || cluster,
          username: currentUser?.username,
        });
        setSshCluster(error.response.data.cluster || (cluster as 'czii' | 'bruno'));
        setSshModalOpen(true);
        setIsSubmitting(false);
        return;
      }

      // Build error message including validation errors if present
      let errorMessage = error instanceof Error ? error.message : 'Failed to submit workflow';
      if (error.validation_errors && error.validation_errors.length > 0) {
        errorMessage += '\n\n' + error.validation_errors.join('\n\n');
      }
      setSubmitError(errorMessage);
      setIsSubmitting(false);
    }
  };

  // Render form field based on schema property
  const renderField = (name: string, prop: any) => {
    // Check if custom field component is provided
    if (customFields && customFields[name]) {
      const CustomField = customFields[name];
      return (
        <CustomField
          key={name}
          name={name}
          schema={prop}
          value={parameters[name]}
          onChange={(value) => handleParameterChange(name, value)}
          error={validationErrors.find((e) => e.field === name)?.message}
          options={dynamicOptions[name]}
        />
      );
    }

    // Check if field is conditional and should be hidden
    const conditional = prop['x-conditional-visibility'] || prop['x-conditional'];
    if (conditional) {
      if (!evaluateConditional(conditional)) {
        return null;
      }
    }

    // Get error for this field
    const error = validationErrors.find((e) => e.field === name);
    const isRequired = schema.schema.required?.includes(name) || false;

    // Build label with CLI flag if available
    const baseLabel = prop.title || name;
    const cliFlag = prop['x-cli-flag'];
    const label = cliFlag ? `${baseLabel} ${cliFlag}` : baseLabel;

    // SLURM/compute resource fields use slurmOptions state, others use parameters
    const isSlurmField = prop['x-compute-resource'] || prop['x-slurm-directive'];
    const stateValue = isSlurmField ? slurmOptions[name] : parameters[name];
    const value = stateValue ?? prop.default ?? '';
    const handleChange = isSlurmField ? handleSlurmOptionChange : handleParameterChange;

    // Handle dynamic dropdowns (e.g., AreTomo3 runs)
    if (prop['x-dynamic-options']) {
      const dynamicOptionsConfig = prop['x-dynamic-options'];
      // Look up options by the source name (if config is object) or field name (if config is true)
      const sourceName =
        typeof dynamicOptionsConfig === 'object' && dynamicOptionsConfig.source ? dynamicOptionsConfig.source : name;
      const options = dynamicOptions[sourceName] || [];

      return (
        <FormControl key={name} fullWidth margin="normal">
          <InputLabel>
            {label}
            {isRequired && <span style={{ color: 'red' }}> *</span>}
          </InputLabel>
          <Select
            value={value}
            onChange={(e) => handleChange(name, e.target.value)}
            disabled={options.length === 0}
            sx={{ bgcolor: 'grey.50' }}
            MenuProps={{
              PaperProps: {
                style: {
                  maxHeight: 300,
                },
              },
            }}
          >
            {options.map((option: FieldOption) => (
              <MenuItem key={option.value} value={option.value}>
                {option.label}
              </MenuItem>
            ))}
          </Select>
          {options.length === 0 ? (
            <FormHelperText>
              {typeof dynamicOptionsConfig === 'object' && dynamicOptionsConfig.depends_on_session
                ? 'Select a session first to see available options'
                : 'No options available'}
            </FormHelperText>
          ) : (
            !!prop.description && <FormHelperText>{prop.description}</FormHelperText>
          )}
        </FormControl>
      );
    }

    // Render based on type
    if (prop.type === 'boolean') {
      return (
        <FormControlLabel
          key={name}
          control={<Switch checked={Boolean(value)} onChange={(e) => handleChange(name, e.target.checked)} />}
          label={
            <Box>
              <Typography variant="body2" fontWeight={isRequired ? 'bold' : 'normal'}>
                {label}
                {isRequired && <span style={{ color: 'red' }}> *</span>}
              </Typography>
              {!!prop.description && (
                <Typography variant="caption" color="text.secondary">
                  {prop.description}
                </Typography>
              )}
            </Box>
          }
        />
      );
    }

    if (prop.enum || dynamicOptions[name]) {
      // Dropdown/select field
      const options = dynamicOptions[name] || prop.enum?.map((v: any) => ({ value: v, label: v })) || [];

      return (
        <TextField
          key={name}
          select
          fullWidth
          label={
            <>
              {label}
              {isRequired && <span style={{ color: 'red' }}> *</span>}
            </>
          }
          value={value}
          onChange={(e) => handleChange(name, e.target.value)}
          helperText={error?.message || prop.description}
          error={Boolean(error)}
          SelectProps={{ native: true }}
          margin="normal"
          sx={{ bgcolor: 'grey.50' }}
        >
          <option value=""></option>
          {options.map((opt: FieldOption) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </TextField>
      );
    }

    // Text/number field
    return (
      <TextField
        key={name}
        fullWidth
        type={prop.type === 'number' ? 'number' : 'text'}
        label={
          <>
            {label}
            {isRequired && <span style={{ color: 'red' }}> *</span>}
          </>
        }
        value={value}
        onChange={(e) => {
          const value = prop.type === 'number' ? parseFloat(e.target.value) : e.target.value;
          handleChange(name, value);
        }}
        helperText={error?.message || prop.description}
        error={Boolean(error)}
        inputProps={{
          min: prop.minimum,
          max: prop.maximum,
          step: prop.type === 'number' ? 'any' : undefined,
        }}
        margin="normal"
        sx={{ bgcolor: 'grey.50' }}
      />
    );
  };

  // Calculate issues preventing submission
  const getIssues = () => {
    const issues: string[] = [];
    // Only check session selection if required
    if (sessionSelectionConfig.requiresSessionSelection) {
      if (!sessionRunSelection.isValid) {
        issues.push('Session or run name not selected');
      }
    } else {
      // For processors that don't require session selection, check generated names
      if (!effectiveSessionName || !effectiveRunName) {
        issues.push('Required parameters not filled for run name generation');
      }
    }
    // Note: lookedUpIds being null is okay for new runs
    if (!dependenciesMet) {
      issues.push('Dependencies not met');
    }
    if (!areRequiredParametersFilled()) {
      const missingFields = schema.schema.required?.filter((field) => {
        const value = parameters[field];
        return value === undefined || value === null || value === '';
      });
      issues.push(`Missing required parameters: ${missingFields?.join(', ') || 'unknown'}`);
    }
    return issues;
  };

  const canSubmit =
    (sessionSelectionConfig.requiresSessionSelection
      ? sessionRunSelection.isValid
      : effectiveSessionName && effectiveRunName) &&
    dependenciesMet &&
    areRequiredParametersFilled();
  const issues = canSubmit ? [] : getIssues();

  return (
    <Box>
      <form onSubmit={handleSubmit}>
        {/* Session Selection - conditional based on processor requirements */}
        {sessionSelectionConfig.requiresSessionSelection && (
          <Box sx={{ mt: 2 }}>
            <SessionRunSelector onChange={setSessionRunSelection} disabled={isSubmitting} />
          </Box>
        )}

        {/* Info message when session selection is not required */}
        {!sessionSelectionConfig.requiresSessionSelection && !!sessionSelectionConfig.hiddenMessage && (
          <Alert severity="info" sx={{ mt: 2 }}>
            {sessionSelectionConfig.hiddenMessage}
          </Alert>
        )}

        {/* Dependency Checker - only show when IDs are available */}
        {lookedUpIds && (
          <DependencyChecker
            pipeInPlanId={lookedUpIds.pipe_in_plan_id}
            procRunId={lookedUpIds.proc_run_id}
            onDependenciesChecked={setDependenciesMet}
          />
        )}

        {/* Section 2 or 3: Configure Parameters (depends on session selection requirement) */}
        {(sessionSelectionConfig.alwaysShowParameters ||
          !sessionSelectionConfig.requiresSessionSelection ||
          sessionRunSelection.isValid) && (
          <>
            <Typography variant="h6" gutterBottom sx={{ mt: 4 }}>
              {sessionSelectionConfig.requiresSessionSelection ? '3' : '2'}. Configure Parameters
            </Typography>

            {/* Additional sections from processor-specific components (Processing Tips) */}
            {additionalSections}

            {/* Loading indicator */}
            {(isLoadingDefaults || isLoadingOptions) && (
              <Alert severity="info" sx={{ my: 2 }}>
                <Box display="flex" alignItems="center">
                  <CircularProgress size={16} sx={{ mr: 1 }} />
                  Loading session data...
                </Box>
              </Alert>
            )}

            {/* Regular Parameters (non-compute-resource, non-grouped) */}
            <Box sx={{ mt: 2 }}>
              {Object.entries(schema.schema.properties)
                .filter(([_name, prop]) => {
                  // Skip compute resource parameters (they go in separate section)
                  if (prop['x-compute-resource']) {
                    return false;
                  }

                  // Skip parameters with parameter group (they go in accordions)
                  if (prop['x-parameter-group']) {
                    return false;
                  }

                  // Skip control-flow parameters
                  if (prop['x-control-flow']) {
                    return false;
                  }

                  // Skip advanced parameters if use_advanced_params is not enabled
                  if (prop['x-advanced'] && !parameters['use_advanced_params']) {
                    return false;
                  }

                  // Skip conditional parameters if their condition is not met
                  const conditional = prop['x-conditional-visibility'] || prop['x-conditional'];
                  if (conditional) {
                    if (!evaluateConditional(conditional)) {
                      return false;
                    }
                  }

                  return true;
                })
                .map(([name, prop]) => renderField(name, prop))}
            </Box>

            {/* Parameter Group Accordions */}
            {(() => {
              // Group parameters by x-parameter-group
              const parameterGroups: Record<string, Array<[string, any]>> = {};
              Object.entries(schema.schema.properties).forEach(([name, prop]) => {
                const group = prop['x-parameter-group'];
                if (group && !prop['x-compute-resource']) {
                  if (!parameterGroups[group]) {
                    parameterGroups[group] = [];
                  }
                  parameterGroups[group].push([name, prop]);
                }
              });

              // Define group titles
              const groupTitles: Record<string, string> = {
                input_processing: 'Input Processing',
                motion_correction: 'Motion Correction',
                gain_dark: 'Gain & Dark Reference',
                alignment: 'Alignment',
                reconstruction: 'Reconstruction',
                ctf: 'CTF Options',
                custom: 'Custom Parameters',
              };

              // Define order
              const groupOrder = [
                'input_processing',
                'motion_correction',
                'gain_dark',
                'alignment',
                'reconstruction',
                'ctf',
                'custom',
              ];

              return Object.entries(parameterGroups)
                .sort(([groupA], [groupB]) => {
                  return groupOrder.indexOf(groupA) - groupOrder.indexOf(groupB);
                })
                .map(([groupName, params]) => (
                  <Accordion key={groupName} sx={{ mt: 2 }} defaultExpanded={false}>
                    <AccordionSummary
                      expandIcon={<ExpandMoreIcon />}
                      sx={{
                        minHeight: 40,
                        py: 1,
                        '&.Mui-expanded': {
                          minHeight: 40,
                        },
                        '& .MuiAccordionSummary-content': {
                          margin: '8px 0',
                        },
                        '& .MuiAccordionSummary-content.Mui-expanded': {
                          margin: '8px 0',
                        },
                      }}
                    >
                      <Typography variant="body1" fontWeight="medium">
                        {groupTitles[groupName] || groupName}
                      </Typography>
                    </AccordionSummary>
                    <AccordionDetails>
                      <Box>
                        {params
                          .filter(([_name, prop]) => {
                            // Still respect conditional visibility (for use_old_gain, use_custom_params)
                            const conditional = prop['x-conditional-visibility'] || prop['x-conditional'];
                            if (conditional) {
                              return evaluateConditional(conditional);
                            }
                            return true;
                          })
                          .map(([name, prop]) => renderField(name, prop))}
                      </Box>
                    </AccordionDetails>
                  </Accordion>
                ));
            })()}

            {/* Compute Resources Section (collapsible) */}
            {Object.entries(schema.schema.properties).some(([_, prop]) => prop['x-compute-resource']) &&
              (() => {
                // Check if this is a hetjob (has x-hetjob-component parameters)
                const hasHetjobComponents = Object.entries(schema.schema.properties).some(
                  ([_, prop]) => prop['x-compute-resource'] && prop['x-hetjob-component'] !== undefined
                );

                if (hasHetjobComponents) {
                  // Group parameters by component number
                  const componentGroups: Record<number, Array<[string, any]>> = {};
                  Object.entries(schema.schema.properties).forEach(([name, prop]) => {
                    if (!prop['x-compute-resource']) return;

                    const componentNum = prop['x-hetjob-component'];
                    if (componentNum !== undefined) {
                      if (!componentGroups[componentNum]) {
                        componentGroups[componentNum] = [];
                      }
                      componentGroups[componentNum].push([name, prop]);
                    }
                  });

                  // Render hetjob layout with side-by-side components
                  return (
                    <Accordion sx={{ mt: 3 }} defaultExpanded={false}>
                      <AccordionSummary
                        expandIcon={<ExpandMoreIcon />}
                        sx={{
                          minHeight: 40,
                          py: 1,
                          '&.Mui-expanded': {
                            minHeight: 40,
                          },
                          '& .MuiAccordionSummary-content': {
                            margin: '8px 0',
                          },
                          '& .MuiAccordionSummary-content.Mui-expanded': {
                            margin: '8px 0',
                          },
                        }}
                      >
                        <Typography variant="body1" fontWeight="medium">
                          Compute Resources
                        </Typography>
                      </AccordionSummary>
                      <AccordionDetails>
                        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                          Adjust SLURM resource allocation for this heterogeneous job. Each component has separate
                          resource requirements.
                        </Typography>
                        <Grid container spacing={3}>
                          {Object.entries(componentGroups)
                            .sort(([a], [b]) => Number(a) - Number(b))
                            .map(([componentNum, params]) => (
                              <Grid item xs={12} md={6} key={componentNum}>
                                <Box
                                  sx={{
                                    p: 2,
                                    border: '1px solid',
                                    borderColor: 'divider',
                                    borderRadius: 1,
                                    height: '100%',
                                  }}
                                >
                                  <Typography variant="subtitle2" fontWeight="medium" sx={{ mb: 2 }}>
                                    Component {componentNum}
                                  </Typography>
                                  {params
                                    .filter(([_name, prop]) => {
                                      // Respect conditional visibility
                                      const conditional = prop['x-conditional-visibility'] || prop['x-conditional'];
                                      if (conditional) {
                                        return evaluateConditional(conditional);
                                      }
                                      return true;
                                    })
                                    .map(([name, prop]) => renderField(name, prop))}
                                </Box>
                              </Grid>
                            ))}
                        </Grid>
                      </AccordionDetails>
                    </Accordion>
                  );
                } else {
                  // Regular (non-hetjob) layout - single column
                  return (
                    <Accordion sx={{ mt: 3 }} defaultExpanded={false}>
                      <AccordionSummary
                        expandIcon={<ExpandMoreIcon />}
                        sx={{
                          minHeight: 40,
                          py: 1,
                          '&.Mui-expanded': {
                            minHeight: 40,
                          },
                          '& .MuiAccordionSummary-content': {
                            margin: '8px 0',
                          },
                          '& .MuiAccordionSummary-content.Mui-expanded': {
                            margin: '8px 0',
                          },
                        }}
                      >
                        <Typography variant="body1" fontWeight="medium">
                          Compute Resources
                        </Typography>
                      </AccordionSummary>
                      <AccordionDetails>
                        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                          Adjust SLURM resource allocation for this job (partition, GPUs, CPUs, memory, time limit).
                        </Typography>
                        <Box>
                          {Object.entries(schema.schema.properties)
                            .filter(([_name, prop]) => {
                              // Only include compute resource parameters
                              if (!prop['x-compute-resource']) {
                                return false;
                              }

                              // Still respect conditional visibility within compute resources
                              const conditional = prop['x-conditional-visibility'] || prop['x-conditional'];
                              if (conditional) {
                                if (!evaluateConditional(conditional)) {
                                  return false;
                                }
                              }

                              return true;
                            })
                            .map(([name, prop]) => renderField(name, prop))}
                        </Box>
                      </AccordionDetails>
                    </Accordion>
                  );
                }
              })()}
          </>
        )}

        {/* Section 3 or 4: Submit (depends on session selection requirement) */}
        {(sessionSelectionConfig.alwaysShowParameters ||
          !sessionSelectionConfig.requiresSessionSelection ||
          sessionRunSelection.isValid) && (
          <>
            <Typography variant="h6" gutterBottom sx={{ mt: 4 }}>
              {sessionSelectionConfig.requiresSessionSelection ? '4' : '3'}. Submit Job
            </Typography>

            {/* Pre-submission summary - only show when ready */}
            {!!canSubmit && (
              <Alert severity="info" sx={{ mt: 2, mb: 2 }}>
                <Typography variant="body2">
                  <strong>Ready to submit:</strong> Job will be submitted to{' '}
                  <strong>
                    {sessionRunSelection.sessionName} / {sessionRunSelection.runName}
                  </strong>{' '}
                  with processor <strong>{processor.name}</strong> on cluster <strong>{cluster.toUpperCase()}</strong>.
                </Typography>
                <Typography variant="body2" sx={{ mt: 1 }}>
                  Note: You may be prompted for SSH credentials if not already configured.
                </Typography>
              </Alert>
            )}

            {/* Issues preventing submission */}
            {issues.length > 0 && (
              <Alert severity="warning" sx={{ mt: 2, mb: 2 }}>
                <Typography variant="body2" fontWeight="bold" gutterBottom>
                  Issues
                </Typography>
                <Box component="ul" sx={{ mt: 1, pl: 2, mb: 0 }}>
                  {issues.map((issue, index) => (
                    <li key={index}>{issue}</li>
                  ))}
                </Box>
              </Alert>
            )}

            {/* Validation errors */}
            {validationErrors.length > 0 && (
              <Alert severity="error" sx={{ mt: 2 }}>
                <Typography variant="subtitle2">Please fix the following errors:</Typography>
                <ul>
                  {validationErrors.map((err, idx) => (
                    <li key={idx}>
                      {err.field !== '__all__' && <strong>{err.field}:</strong>} {err.message}
                    </li>
                  ))}
                </ul>
              </Alert>
            )}

            {/* Submit error */}
            {!!submitError && (
              <Alert severity="error" sx={{ mt: 2 }}>
                {submitError}
              </Alert>
            )}

            {/* Success message */}
            {submitSuccess && (
              <Alert severity="success" icon={<CheckCircleIcon />} sx={{ mt: 2 }}>
                <Typography variant="body1" fontWeight="bold">
                  Workflow submitted successfully!
                </Typography>
                {executionResult && (
                  <>
                    {executionResult.job_id && (
                      <Typography variant="body2">
                        SLURM Job ID: <strong>{executionResult.job_id}</strong>
                      </Typography>
                    )}
                    {executionResult.pipe_execution_id && (
                      <Typography variant="body2">
                        Execution ID: <strong>{executionResult.pipe_execution_id}</strong>
                      </Typography>
                    )}
                  </>
                )}
                <Typography variant="body2" sx={{ mt: 1 }}>
                  Redirecting to monitoring page...
                </Typography>
              </Alert>
            )}

            {/* Preview and Submit buttons side-by-side */}
            <Box sx={{ display: 'flex', gap: 2, mt: 2 }}>
              <Button
                variant="outlined"
                color="secondary"
                size="large"
                fullWidth
                startIcon={<VisibilityIcon />}
                disabled={!canSubmit || isSubmitting}
                onClick={handlePreviewScript}
              >
                Preview SLURM Script
              </Button>

              <Button
                type="submit"
                variant="contained"
                color="primary"
                size="large"
                fullWidth
                startIcon={isSubmitting ? <CircularProgress size={20} /> : <PlayArrowIcon />}
                disabled={isSubmitting || !canSubmit}
              >
                {isSubmitting ? 'Submitting...' : 'Submit Job'}
              </Button>
            </Box>
          </>
        )}
      </form>

      {/* SSH Setup Modal - rendered outside form to avoid z-index issues */}
      {!!currentUser?.username && (
        <SSHSetupModal
          open={sshModalOpen}
          onClose={() => setSshModalOpen(false)}
          onSuccess={handleSSHSetupSuccess}
          cluster={sshCluster}
          username={currentUser.username}
        />
      )}

      {/* Script Preview Modal */}
      <ScriptPreviewModal
        open={previewModalOpen}
        onClose={() => setPreviewModalOpen(false)}
        scriptContent={previewScript}
        isLoading={isLoadingPreview}
        error={previewError}
        jobName={`${processor.name}_${sessionRunSelection.sessionName}_${sessionRunSelection.runName}`}
      />
    </Box>
  );
}
