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
import { useEffect, useMemo, useRef, useState } from 'react';
import type { SessionSelectionConfig, ValidationError, WorkflowLaunchFormProps } from '@app/common/types/workflow';
import WorkflowLaunchForm from './WorkflowLaunchForm';

interface CopickLaunchFormProps
  extends Omit<WorkflowLaunchFormProps, 'customFields' | 'additionalSections' | 'customValidation'> {
  // No additional props needed for now
}

export default function CopickLaunchForm(props: CopickLaunchFormProps) {
  const [operationMode, setOperationMode] = useState<string>('create');
  const lastSyncedValueRef = useRef<string>('create');

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
   * Using useMemo to create stable component references and prevent infinite loops
   */
  const customFields: Record<string, React.ComponentType<any>> = useMemo(
    () => ({
      // Hide operation field from rendering (tabs handle the UI)
      // but keep it synced with form parameters for conditional visibility
      operation: ({ onChange }: any) => {
        // One-way sync: operationMode state -> form parameter
        // Only call onChange if the value actually changed (prevents infinite loops)
        useEffect(() => {
          if (onChange && operationMode !== lastSyncedValueRef.current) {
            lastSyncedValueRef.current = operationMode;
            onChange(operationMode);
          }
        }, [operationMode, onChange]);

        // Don't render anything (tabs are in additionalSections)
        return null;
      },
    }),
    [operationMode]
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
        generateSessionName: (params) => params.copick_session || null,
        generateRunName: (params) => {
          if (params.copick_session && params.copick_run) {
            return `${params.copick_session}_add_object_${params.copick_run}`;
          }
          return null;
        },
        hiddenMessage: 'Working on existing Copick project - no MSI session selection needed',
      };
    } else if (operationMode === 'import_tomograms') {
      return {
        requiresSessionSelection: false,
        alwaysShowParameters: true, // Show parameters section to allow mode switching via tabs
        generateSessionName: (params) => params.copick_session || null,
        generateRunName: (params) => {
          if (params.copick_session && params.copick_run) {
            return `${params.copick_session}_import_tomograms_${params.copick_run}`;
          }
          return null;
        },
        hiddenMessage: 'Importing to existing Copick project - no MSI session selection needed',
      };
    }
    return { requiresSessionSelection: true, alwaysShowParameters: true };
  }, [operationMode]);

  /**
   * Custom validation for Copick parameters
   */
  const customValidation = async (parameters: Record<string, any>): Promise<ValidationError[]> => {
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

  return (
    <WorkflowLaunchForm
      {...props}
      sessionSelectionConfig={sessionSelectionConfig}
      customFields={customFields}
      customValidation={customValidation}
      additionalSections={[tabsSection]} // Render tabs at top of Configure Parameters
    />
  );
}
