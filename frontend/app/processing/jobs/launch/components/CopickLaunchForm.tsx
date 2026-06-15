'use client';

/**
 * CopickLaunchForm - Processor-specific launch form for Copick workflows
 *
 * Supports three operation modes via tabs:
 * 1. Create: Create new Copick project with tomograms
 * 2. Add Object: Add pickable objects to existing Copick project
 * 3. Import Tomograms: Import additional tomograms to existing project
 *
 * Features:
 * - Tab-based UI for operation mode selection (rendered at top of Configure Parameters)
 * - Dynamic loading of template maps
 * - Dynamic loading of Copick runs
 * - Auto-fill object diameter from selected template map
 * - Conditional field visibility based on selected operation mode
 */

import { Alert, Box, Tab, Tabs, Typography } from '@mui/material';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type {
  FieldOption,
  FormFieldConfig,
  SessionSelectionConfig,
  ValidationError,
  WorkflowLaunchFormProps,
} from '@app/common/types/workflow';
import { fetchProcessorOptions } from '@app/common/services/workflowApi';
import { fetchCopickImportRuns, fetchCopickObjectRuns } from '../services/copickApi';
import WorkflowLaunchForm from './WorkflowLaunchForm';

/**
 * Hidden field component that syncs operation mode to form parameters.
 * Defined outside the parent component to comply with React hooks rules.
 */
interface OperationFieldProps {
  operationMode: string;
  lastSyncedValueRef: React.MutableRefObject<string>;
  onChange?: (value: unknown) => void;
}

function OperationField({ operationMode, lastSyncedValueRef, onChange }: OperationFieldProps) {
  useEffect(() => {
    if (onChange && operationMode !== lastSyncedValueRef.current) {
      lastSyncedValueRef.current = operationMode;
      onChange(operationMode);
    }
  }, [onChange, operationMode, lastSyncedValueRef]);

  // Don't render anything (tabs are in additionalSections)
  return null;
}

type CopickLaunchFormProps = Omit<WorkflowLaunchFormProps, 'customFields' | 'additionalSections' | 'customValidation'>;

export default function CopickLaunchForm(props: CopickLaunchFormProps) {
  const [operationMode, setOperationMode] = useState<string>('create');
  const [nextRunName, setNextRunName] = useState<string>('run001');
  const [nextImportRunName, setNextImportRunName] = useState<string>('run001');
  const lastSyncedValueRef = useRef<string>('create');

  // Track the selected copick session to fetch the next available run name
  // Numbering is per-session (run001, run002, etc.) - matches standard proc run naming
  // Updated via generateRunName callback when user selects copick_session
  const [selectedCopickSession, setSelectedCopickSession] = useState<string | null>(null);
  const [selectedImportSession, setSelectedImportSession] = useState<string | null>(null);

  // Dynamic options managed by this form (for add_object/import_tomograms modes)
  const [copickDynamicOptions, setCopickDynamicOptions] = useState<Record<string, FieldOption[]>>({});

  // Track previous parameter values to avoid redundant fetches
  const prevParamsRef = useRef<{ copick_session?: string; import_tomo_type?: string; sessionName?: string | null }>({});

  /**
   * Handle parameter changes from WorkflowLaunchForm.
   * Fetches dynamic options when copick_session or import_tomo_type changes.
   */
  const handleParametersChange = useCallback(
    async (parameters: Record<string, unknown>, sessionName: string | null) => {
      const copickSession = parameters.copick_session as string | undefined;
      const importTomoType = parameters.import_tomo_type as string | undefined;

      // Check if relevant parameters changed
      const prev = prevParamsRef.current;
      const copickSessionChanged = copickSession !== prev.copick_session;
      const importTomoTypeChanged = importTomoType !== prev.import_tomo_type;
      const sessionNameChanged = sessionName !== prev.sessionName;

      // Update tracked values
      prevParamsRef.current = { copick_session: copickSession, import_tomo_type: importTomoType, sessionName };

      // Load initial options (copick_session list) on first load
      if (!prev.copick_session && !prev.import_tomo_type && !copickSession) {
        try {
          const optionsResult = await fetchProcessorOptions(props.processor.name, undefined, undefined);
          setCopickDynamicOptions(optionsResult.options);
        } catch (error) {
          console.error('Failed to load initial copick options:', error);
        }
        return;
      }

      // Skip if MSI session is selected (create mode handles its own options)
      if (sessionName) {
        // But still refetch when import_tomo_type changes in create mode
        if (importTomoTypeChanged && importTomoType) {
          try {
            const optionsResult = await fetchProcessorOptions(props.processor.name, sessionName, {
              import_tomo_type: importTomoType,
            });
            setCopickDynamicOptions((prev) => ({ ...prev, ...optionsResult.options }));
          } catch (error) {
            console.error('Failed to refetch options for import_tomo_type change:', error);
          }
        }
        return;
      }

      // For add_object/import_tomograms modes: refetch when copick_session or import_tomo_type changes
      if ((copickSessionChanged || importTomoTypeChanged || sessionNameChanged) && copickSession) {
        try {
          const additionalParams: Record<string, string | number> = {
            copick_session: copickSession,
          };
          if (importTomoType) {
            additionalParams.import_tomo_type = importTomoType;
          }
          const optionsResult = await fetchProcessorOptions(
            props.processor.name,
            copickSession, // Use copick_session as session_id for import_tomogram_run lookup
            additionalParams
          );
          setCopickDynamicOptions((prev) => ({ ...prev, ...optionsResult.options }));
        } catch (error) {
          console.error('Failed to refetch copick options:', error);
        }
      }
    },
    [props.processor.name]
  );

  // Fetch next available run name when copick session changes (for add_object mode)
  // Pattern matches WorkflowLaunchForm's useEffect-based data fetching
  useEffect(() => {
    if (!selectedCopickSession || operationMode !== 'add_object') {
      return;
    }

    const loadNextCopickObjectRunName = async () => {
      try {
        const data = await fetchCopickObjectRuns(selectedCopickSession);
        setNextRunName(data.next_run_name);
      } catch {
        // Default to run001 if fetch fails
        setNextRunName('run001');
      }
    };

    loadNextCopickObjectRunName();
  }, [selectedCopickSession, operationMode]);

  // Fetch next available run name when copick session changes (for import_tomograms mode)
  useEffect(() => {
    if (!selectedImportSession || operationMode !== 'import_tomograms') {
      return;
    }

    const loadNextImportRunName = async () => {
      try {
        const data = await fetchCopickImportRuns(selectedImportSession);
        setNextImportRunName(data.next_run_name);
      } catch {
        // Default to run001 if fetch fails
        setNextImportRunName('run001');
      }
    };

    loadNextImportRunName();
  }, [selectedImportSession, operationMode]);

  /**
   * Tabs section rendered at top of Configure Parameters
   * Moved from customFields to additionalSections to avoid accordion wrapping
   */
  const tabsSection = useMemo(
    () => (
      <Box sx={{ mb: 3 }} key="operation-tabs">
        <Tabs
          value={operationMode}
          onChange={(_, newValue) => setOperationMode(newValue)}
          aria-label="Copick operation modes"
          sx={{ borderBottom: 1, borderColor: 'divider' }}
        >
          <Tab label="Create Project" value="create" />
          <Tab label="Add Object" value="add_object" />
          <Tab label="Import Tomograms" value="import_tomograms" />
        </Tabs>

        {/* Tab Descriptions */}
        <Box sx={{ mt: 2 }}>
          {operationMode === 'create' && (
            <Alert severity="info">
              <Typography variant="body2">
                Create a new Copick project and import tomograms from an existing processing run.
              </Typography>
            </Alert>
          )}
          {operationMode === 'add_object' && (
            <Alert severity="info">
              <Typography variant="body2">
                Add pickable object definitions to an existing Copick project. Select a template map or provide a custom
                object map file.
              </Typography>
            </Alert>
          )}
          {operationMode === 'import_tomograms' && (
            <Alert severity="info">
              <Typography variant="body2">
                Import additional tomograms to an existing Copick project from a processing run.
              </Typography>
            </Alert>
          )}
        </Box>
      </Box>
    ),
    [operationMode]
  );

  /**
   * Custom field components for Copick-specific fields
   * Operation field is hidden but maintains sync with form parameters
   */
  // Create a wrapper component that passes the current operationMode to OperationField
  const OperationFieldWrapper = useMemo(() => {
    const Wrapper = (props: FormFieldConfig) => (
      <OperationField operationMode={operationMode} lastSyncedValueRef={lastSyncedValueRef} onChange={props.onChange} />
    );
    Wrapper.displayName = 'OperationFieldWrapper';
    return Wrapper;
  }, [operationMode]);

  const customFields: Record<string, React.ComponentType<FormFieldConfig>> = useMemo(
    () => ({
      // Hide operation field from rendering (tabs handle the UI)
      // but keep it synced with form parameters for conditional visibility
      operation: OperationFieldWrapper,
    }),
    [OperationFieldWrapper]
  );

  /**
   * Session selection configuration based on operation mode
   * - Create mode: Requires MSI session selection (existing behavior)
   * - Add Object mode: Works on existing Copick session (NO MSI session needed)
   * - Import mode: Works on existing Copick project (NO MSI session needed)
   */
  const sessionSelectionConfig: SessionSelectionConfig = useMemo(() => {
    if (operationMode === 'create') {
      return {
        requiresSessionSelection: true,
        alwaysShowParameters: true, // Show parameters section to allow mode switching via tabs
      };
    } else if (operationMode === 'add_object') {
      return {
        requiresSessionSelection: false,
        alwaysShowParameters: true, // Show parameters section to allow mode switching via tabs
        generateSessionName: (params) => (params.copick_session as string) || null,
        generateRunName: (params) => {
          const copickSession = params.copick_session as string;
          // Track session changes to trigger run name lookup via useEffect
          // Note: setState during render is handled by React (schedules update for next render)
          if (copickSession && copickSession !== selectedCopickSession) {
            setSelectedCopickSession(copickSession);
          }
          return copickSession ? nextRunName : null;
        },
      };
    } else if (operationMode === 'import_tomograms') {
      return {
        requiresSessionSelection: false,
        alwaysShowParameters: true, // Show parameters section to allow mode switching via tabs
        generateSessionName: (params) => (params.copick_session as string) || null,
        generateRunName: (params) => {
          const copickSession = params.copick_session as string;
          // Track session changes to trigger run name lookup via useEffect
          if (copickSession && copickSession !== selectedImportSession) {
            setSelectedImportSession(copickSession);
          }
          return copickSession ? nextImportRunName : null;
        },
      };
    }
    return { requiresSessionSelection: true, alwaysShowParameters: true };
  }, [operationMode, nextRunName, selectedCopickSession, nextImportRunName, selectedImportSession]);

  /**
   * Custom validation for Copick parameters
   */
  const customValidation = async (parameters: Record<string, unknown>): Promise<ValidationError[]> => {
    const errors: ValidationError[] = [];

    const operation = parameters.operation || 'create';

    // Validate add_object mode
    if (operation === 'add_object') {
      // Require copick_session and copick_run
      if (!parameters.copick_session) {
        errors.push({
          field: 'copick_session',
          message: 'Copick session is required for Add Object mode',
        });
      }
      if (!parameters.copick_run) {
        errors.push({
          field: 'copick_run',
          message: 'Copick run is required for Add Object mode',
        });
      }

      // Require either template_map_name or object_map_file
      if (!parameters.template_map_name && !parameters.object_map_file) {
        errors.push({
          field: 'template_map_name',
          message: 'Either select a template map or provide a custom object map file',
        });
      }

      // If custom map file provided, voxel size is required
      if (parameters.object_map_file && !parameters.object_voxel_size) {
        errors.push({
          field: 'object_voxel_size',
          message: 'Voxel size is required when using a custom object map file',
        });
      }
    }

    // Validate import_tomograms mode
    if (operation === 'import_tomograms') {
      if (!parameters.copick_session) {
        errors.push({
          field: 'copick_session',
          message: 'Copick session is required for Import Tomograms mode',
        });
      }
      if (!parameters.copick_run) {
        errors.push({
          field: 'copick_run',
          message: 'Copick run is required for Import Tomograms mode',
        });
      }
    }

    return errors;
  };

  /**
   * Override processor name based on operation mode.
   * - add_object and import_tomograms use separate plans for tracking
   */
  const getProcessorName = useCallback((params: Record<string, unknown>) => {
    if (params.operation === 'add_object') return 'copick-add-object';
    if (params.operation === 'import_tomograms') return 'copick-import';
    return 'copick';
  }, []);

  /**
   * Pre-submission hook to clean up parameters based on operation mode.
   * - For "create" mode: removes copick_session (auto-defaulted but not user-selected)
   *   and adds mode-specific parameters
   */
  const onBeforeSubmit = useCallback(
    async (
      params: Record<string, unknown>,
      context: { sessionName: string | null; runName: string | null }
    ): Promise<Record<string, unknown>> => {
      const operation = params.operation || 'create';

      if (operation === 'create') {
        const cleanedParams = Object.fromEntries(Object.entries(params).filter(([key]) => key !== 'copick_session'));
        return {
          ...cleanedParams,
          msi_session_used: context.sessionName,
          create_copick_project_run: context.runName,
        };
      }

      // For add_object and import_tomograms, keep copick_session as-is (user-selected)
      return params;
    },
    []
  );

  return (
    <WorkflowLaunchForm
      {...props}
      sessionSelectionConfig={sessionSelectionConfig}
      customFields={customFields}
      customValidation={customValidation}
      additionalSections={[tabsSection]} // Render tabs at top of Configure Parameters
      getProcessorName={getProcessorName}
      onBeforeSubmit={onBeforeSubmit}
      onParametersChange={handleParametersChange}
      externalDynamicOptions={copickDynamicOptions}
    />
  );
}
