'use client';

/**
 * MembranesegLaunchForm - Processor-specific launch form for Membrane Segmentation
 *
 * Features:
 * - No MSI session selection (uses Copick session instead)
 * - Cascading dropdowns: copick_session → copick_procrun → tomo_type → tomo_voxel_size
 * - Dynamic loading of options from backend
 * - Custom session/run name generation from parameters
 */

import { Alert, Box, Typography } from '@mui/material';
import { useCallback, useEffect, useMemo, useState } from 'react';
import type { SessionSelectionConfig, ValidationError, WorkflowLaunchFormProps } from '@app/common/types/workflow';
import WorkflowLaunchForm from './WorkflowLaunchForm';
import { fetchMembranesegRuns } from '../services/membranesegApi';

type MembranesegLaunchFormProps = Omit<
  WorkflowLaunchFormProps,
  'customFields' | 'additionalSections' | 'customValidation'
>;

export default function MembranesegLaunchForm(props: MembranesegLaunchFormProps) {
  const [selectedCopickSession, setSelectedCopickSession] = useState<string | null>(null);
  const [nextRunName, setNextRunName] = useState<string>('run001');

  // Fetch next available run name when copick session changes
  useEffect(() => {
    if (!selectedCopickSession) {
      return;
    }

    const loadNextRunName = async () => {
      try {
        const data = await fetchMembranesegRuns(selectedCopickSession);
        setNextRunName(data.next_run_name);
      } catch {
        // Default to run001 if fetch fails
        setNextRunName('run001');
      }
    };

    loadNextRunName();
  }, [selectedCopickSession]);

  /**
   * Info section rendered at top of Configure Parameters
   */
  const infoSection = useMemo(
    () => (
      <Box sx={{ mb: 3 }} key="membraneseg-info">
        <Alert severity="info">
          <Typography variant="body2">
            Membrane Segmentation runs membrain-seg inference on Copick tomograms. Select a Copick session and
            processing run that contains imported tomograms.
          </Typography>
        </Alert>
      </Box>
    ),
    []
  );

  /**
   * Session selection configuration
   * - No MSI session selection needed (uses Copick session from parameters)
   * - Generates session/run names from copick_session and copick_procrun
   */
  // Track copick_session changes via onParametersChange callback (not during render)
  const handleParametersChange = useCallback(
    (params: Record<string, unknown>) => {
      const copickSession = params.copick_session as string;
      if (copickSession && copickSession !== selectedCopickSession) {
        setSelectedCopickSession(copickSession);
      }
    },
    [selectedCopickSession]
  );

  const sessionSelectionConfig: SessionSelectionConfig = useMemo(
    () => ({
      requiresSessionSelection: false,
      alwaysShowParameters: true,
      generateSessionName: (params) => (params.copick_session as string) || null,
      generateRunName: (params) => {
        const copickSession = params.copick_session as string;
        return copickSession ? nextRunName : null;
      },
    }),
    [nextRunName]
  );

  /**
   * Custom validation for membrane segmentation parameters
   */
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const customValidation = async (parameters: Record<string, any>): Promise<ValidationError[]> => {
    const errors: ValidationError[] = [];

    // Required fields
    if (!parameters.copick_session) {
      errors.push({
        field: 'copick_session',
        message: 'Copick session is required',
      });
    }
    if (!parameters.copick_procrun) {
      errors.push({
        field: 'copick_procrun',
        message: 'Copick run is required',
      });
    }
    if (!parameters.tomo_type) {
      errors.push({
        field: 'tomo_type',
        message: 'Tomogram type is required',
      });
    }
    if (!parameters.tomo_voxel_size) {
      errors.push({
        field: 'tomo_voxel_size',
        message: 'Tomogram voxel size is required',
      });
    }

    // Validate threshold if provided
    if (parameters.threshold !== undefined && parameters.threshold !== '') {
      const threshold = parseFloat(parameters.threshold);
      if (isNaN(threshold)) {
        errors.push({
          field: 'threshold',
          message: 'Threshold must be a valid number',
        });
      }
    }

    return errors;
  };

  return (
    <WorkflowLaunchForm
      {...props}
      sessionSelectionConfig={sessionSelectionConfig}
      customValidation={customValidation}
      additionalSections={[infoSection]}
      onParametersChange={handleParametersChange}
    />
  );
}
