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
  FormFieldConfig,
  SessionSelectionConfig,
  ValidationError,
  WorkflowLaunchFormProps,
} from '@app/common/types/workflow';
import { fetchCopickObjectRuns } from '@app/common/services/workflowApi';
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

interface CopickLaunchFormProps
  extends Omit<WorkflowLaunchFormProps, 'customFields' | 'additionalSections' | 'customValidation'> {
  // No additional props needed for now
}

export default function CopickLaunchForm(props: CopickLaunchFormProps) {
  const [operationMode, setOperationMode] = useState<string>('create');
  const [nextRunName, setNextRunName] = useState<string>('run001');
  const lastSyncedValueRef = useRef<string>('create');

  // Track the selected copick session to fetch the next available run name
  // Numbering is per-session (run001, run002, etc.) - matches standard proc run naming
  // Updated via generateRunName callback when user selects copick_session
  const [selectedCopickSession, setSelectedCopickSession] = useState<string | null>(null);

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
        hiddenMessage: 'Working on existing Copick project - no MSI session selection needed',
      };
    } else if (operationMode === 'import_tomograms') {
      return {
        requiresSessionSelection: false,
        alwaysShowParameters: true, // Show parameters section to allow mode switching via tabs
        generateSessionName: (params) => (params.copick_session as string) || null,
        generateRunName: (params) => {
          if (params.copick_session && params.copick_run) {
            // TODO: Will structure like copick add
            return `${params.copick_session}_import_tomograms_${params.copick_run}`;
          }
          return null;
        },
        hiddenMessage: 'Importing to existing Copick project - no MSI session selection needed',
      };
    }
    return { requiresSessionSelection: true, alwaysShowParameters: true };
  }, [operationMode, nextRunName, selectedCopickSession]);

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
   * - add_object uses copick-add-object processor (separate plan for tracking)
   * - create and import_tomograms use copick processor
   */
  const getProcessorName = useCallback((params: Record<string, unknown>) => {
    return params.operation === 'add_object' ? 'copick-add-object' : 'copick';
  }, []);

  return (
    <WorkflowLaunchForm
      {...props}
      sessionSelectionConfig={sessionSelectionConfig}
      customFields={customFields}
      customValidation={customValidation}
      additionalSections={[tabsSection]} // Render tabs at top of Configure Parameters
      getProcessorName={getProcessorName}
    />
  );
}
