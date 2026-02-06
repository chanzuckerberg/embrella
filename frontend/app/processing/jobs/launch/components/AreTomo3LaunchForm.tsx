'use client';

/**
 * AreTomo3LaunchForm - Processor-specific launch form for AreTomo3
 *
 * Extends the base WorkflowLaunchForm with AreTomo3-specific features:
 * - Custom validation for dose-related parameters
 * - Session-specific file options (gain files, etc.)
 * - Custom help text and documentation
 * - CLI command import for pre-populating form from prior runs
 */

import { Alert, Box } from '@mui/material';
import { useState } from 'react';
import { Button, Icon } from '@czi-sds/components';
import type { ValidationError, WorkflowLaunchFormProps, HeaderActionsContext } from '@app/common/types/workflow';
import WorkflowLaunchForm from './WorkflowLaunchForm';
import CLIParserModal from './CLIParserModal';

interface AreTomo3LaunchFormProps
  extends Omit<WorkflowLaunchFormProps, 'customFields' | 'additionalSections' | 'customValidation' | 'headerActions'> {
  // No additional props needed for now
}

export default function AreTomo3LaunchForm(props: AreTomo3LaunchFormProps) {
  const [doseWarning, setDoseWarning] = useState<string | null>(null);
  const [cliParserOpen, setCliParserOpen] = useState(false);

  /**
   * Custom validation for AreTomo3 parameters
   *
   * NOTE: This validation is SUPPLEMENTARY to automatic JSON schema validation.
   * The schema (aretomo3/schema.yaml) already validates:
   * - Required fields (pixel_size, total_dose, frame_dose)
   * - Min/max ranges (pixel_size: 0.5-20, tilt_axis: -180 to 180, etc.)
   * - Field types and enums
   *
   * Use this for domain-specific validation that can't be expressed in JSON schema.
   *
   * To add a hard validation error that prevents submission:
   *   errors.push({
   *     field: 'parameter_name',
   *     message: 'Error message shown to user',
   *   });
   */
  const customValidation = async (parameters: Record<string, unknown>): Promise<ValidationError[]> => {
    const errors: ValidationError[] = [];

    // Validate dose calculations if tilt metadata is available
    if (parameters.pixel_size && parameters.dose_per_tilt) {
      const pixelSize = parseFloat(String(parameters.pixel_size));
      const dosePerTilt = parseFloat(String(parameters.dose_per_tilt));

      if (pixelSize <= 0) {
        errors.push({
          field: 'pixel_size',
          message: 'Pixel size must be greater than 0',
        });
      }

      if (dosePerTilt <= 0) {
        errors.push({
          field: 'dose_per_tilt',
          message: 'Dose per tilt must be greater than 0',
        });
      }

      // Warn if dose is unusually high or low
      if (dosePerTilt > 0) {
        if (dosePerTilt < 1) {
          setDoseWarning('Warning: Dose per tilt is unusually low (<1 e⁻/Ų). Please verify.');
        } else if (dosePerTilt > 10) {
          setDoseWarning('Warning: Dose per tilt is unusually high (>10 e⁻/Ų). Please verify.');
        } else {
          setDoseWarning(null);
        }
      }
    }

    // Validate alignment parameters
    if (parameters.tilt_axis_angle !== undefined) {
      const angle = parseFloat(String(parameters.tilt_axis_angle));
      if (angle < -180 || angle > 180) {
        errors.push({
          field: 'tilt_axis_angle',
          message: 'Tilt axis angle must be between -180 and 180 degrees',
        });
      }
    }

    // Validate binning factor
    if (parameters.binning) {
      const binning = parseInt(String(parameters.binning));
      if (binning < 1 || binning > 8) {
        errors.push({
          field: 'binning',
          message: 'Binning factor must be between 1 and 8',
        });
      }
    }

    return errors;
  };

  /**
   * Additional UI sections specific to AreTomo3
   */
  const additionalSections = (
    <Box key="aretomo3-additional" sx={{ mt: 3 }}>
      {/* Dose warning if present */}
      {!!doseWarning && (
        <Alert severity="warning" sx={{ mb: 2 }}>
          {doseWarning}
        </Alert>
      )}
    </Box>
  );

  /**
   * Header actions for AreTomo3 - includes CLI import button
   */
  const headerActions = ({ setParameters, schema }: HeaderActionsContext) => (
    <>
      <Button
        sdsType="secondary"
        sdsStyle="rounded"
        startIcon={<Icon sdsIcon="Code" sdsSize="s" />}
        onClick={() => setCliParserOpen(true)}
      >
        Import from CLI
      </Button>
      <CLIParserModal
        open={cliParserOpen}
        onClose={() => setCliParserOpen(false)}
        onApply={(parsedParams) => {
          setParameters((prev) => ({ ...prev, ...parsedParams }));
        }}
        schema={schema}
      />
    </>
  );

  return (
    <WorkflowLaunchForm
      {...props}
      customValidation={customValidation}
      additionalSections={[additionalSections]}
      headerActions={headerActions}
    />
  );
}
