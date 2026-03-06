'use client';

/**
 * AreTomo3LaunchForm - Processor-specific launch form for AreTomo3
 *
 * Extends the base WorkflowLaunchForm with AreTomo3-specific features:
 * - Custom validation for dose-related parameters
 * - Session-specific file options (gain files, etc.)
 * - Custom help text and documentation
 * - CLI command import for pre-populating form from prior runs
 * - MDOC magnification validation for pixel size verification
 */

import { Alert, Box, CircularProgress, Typography } from '@mui/material';
import { useCallback, useState } from 'react';
import { Button, Icon } from '@czi-sds/components';
import type { ValidationError, WorkflowLaunchFormProps, HeaderActionsContext } from '@app/common/types/workflow';
import { fetchProcessorSessionValidation } from '@app/common/services/workflowApi';
import WorkflowLaunchForm from './WorkflowLaunchForm';
import CLIParserModal from './CLIParserModal';

interface PixelSizeValidation {
  mdocMagnification?: number;
  mdocFile?: string;
  mismatch?: boolean;
  missing?: boolean;
  warning?: string;
  suggestedPixelSize?: number;
  suggestedMagnification?: number;
  error?: string;
}

interface AreTomo3LaunchFormProps
  extends Omit<
    WorkflowLaunchFormProps,
    'customFields' | 'additionalSections' | 'customValidation' | 'headerActions' | 'onSessionInfoLoaded'
  > {
  // No additional props needed for now
}

export default function AreTomo3LaunchForm(props: AreTomo3LaunchFormProps) {
  const [doseWarning, setDoseWarning] = useState<string | null>(null);
  const [cliParserOpen, setCliParserOpen] = useState(false);
  const [pixelSizeValidation, setPixelSizeValidation] = useState<PixelSizeValidation>({});
  const [isValidating, setIsValidating] = useState(false);

  const handleSessionInfoLoaded = useCallback(
    (_sessionInfo: Record<string, unknown>, sessionName: string) => {
      // Fire async MDOC magnification validation (separate from defaults to avoid blocking form)
      setPixelSizeValidation({});
      setIsValidating(true);
      fetchProcessorSessionValidation(props.processor.name, sessionName)
        .then((result) => {
          const v = result.validation;
          setPixelSizeValidation({
            mdocMagnification: v.mdoc_magnification as number | undefined,
            mdocFile: v.mdoc_file as string | undefined,
            mismatch: v.mismatch as boolean | undefined,
            missing: v.missing as boolean | undefined,
            warning: v.warning as string | undefined,
            suggestedPixelSize: v.suggested_pixel_size as number | undefined,
            suggestedMagnification: v.suggested_magnification as number | undefined,
            error: v.error as string | undefined,
          });
        })
        .catch((err) => {
          setPixelSizeValidation({ error: String(err) });
        })
        .finally(() => {
          setIsValidating(false);
        });
    },
    [props.processor.name]
  );

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
      {/* MDOC pixel size validation */}
      {isValidating && (
        <Alert severity="info" icon={<CircularProgress size={20} />} sx={{ mb: 2 }}>
          Verifying pixel size against MDOC file...
        </Alert>
      )}
      {pixelSizeValidation.mismatch === true && (
        <Alert severity="warning" sx={{ mb: 2 }}>
          <Typography variant="body2" fontWeight="bold" gutterBottom>
            Magnification Mismatch
          </Typography>
          <Typography variant="body2">{pixelSizeValidation.warning}</Typography>
          {pixelSizeValidation.suggestedPixelSize !== undefined && (
            <Typography variant="body2" sx={{ mt: 0.5 }}>
              Based on MDOC magnification ({pixelSizeValidation.suggestedMagnification}x), the expected pixel size is{' '}
              <strong>{pixelSizeValidation.suggestedPixelSize} A/px</strong>.
            </Typography>
          )}
          {pixelSizeValidation.mdocFile && (
            <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5, display: 'block' }}>
              Source: {pixelSizeValidation.mdocFile}
            </Typography>
          )}
        </Alert>
      )}
      {pixelSizeValidation.missing === true && (
        <Alert severity="info" sx={{ mb: 2 }}>
          <Typography variant="body2">{pixelSizeValidation.warning}</Typography>
          {pixelSizeValidation.suggestedPixelSize !== undefined && (
            <Typography variant="body2" sx={{ mt: 0.5 }}>
              Based on MDOC magnification ({pixelSizeValidation.suggestedMagnification}x), the expected pixel size is{' '}
              <strong>{pixelSizeValidation.suggestedPixelSize} A/px</strong>.
            </Typography>
          )}
          {pixelSizeValidation.mdocFile && (
            <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5, display: 'block' }}>
              Source: {pixelSizeValidation.mdocFile}
            </Typography>
          )}
        </Alert>
      )}
      {pixelSizeValidation.error && pixelSizeValidation.mismatch === undefined && (
        <Alert severity="info" sx={{ mb: 2 }}>
          Could not verify magnification from MDOC file: {pixelSizeValidation.error}
        </Alert>
      )}
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
      onSessionInfoLoaded={handleSessionInfoLoaded}
    />
  );
}
