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

import { Alert, Box, CircularProgress, InputAdornment, TextField } from '@mui/material';
import { useCallback, useState } from 'react';
import { Button, Icon, Tooltip } from '@czi-sds/components';
import type {
  FormFieldConfig,
  ValidationError,
  WorkflowLaunchFormProps,
  HeaderActionsContext,
} from '@app/common/types/workflow';
import { fetchProcessorSessionValidation } from '@app/common/services/workflowApi';
import WorkflowLaunchForm from './WorkflowLaunchForm';
import CLIParserModal from './CLIParserModal';
import { PIXEL_SIZE_DECIMALS, resolvedPixelSize, SUPER_RES_FACTOR } from '../utils/pixelSize';

/** The two form parameters the motion-corrected pixel size depends on. */
interface BinningParams {
  mcBin: unknown;
  eerSampling: unknown;
}

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

type AreTomo3LaunchFormProps = Omit<
  WorkflowLaunchFormProps,
  | 'customFields'
  | 'additionalSections'
  | 'customValidation'
  | 'headerActions'
  | 'onSessionInfoLoaded'
  | 'onParametersChange'
>;

export default function AreTomo3LaunchForm(props: AreTomo3LaunchFormProps) {
  const [doseWarning, setDoseWarning] = useState<string | null>(null);
  const [cliParserOpen, setCliParserOpen] = useState(false);
  const [pixelSizeValidation, setPixelSizeValidation] = useState<PixelSizeValidation>({});
  const [isValidating, setIsValidating] = useState(false);
  // Super-res is a session fact, hidden from the form; it halves the frame pixel the tooltip resolves.
  const [superResolution, setSuperResolution] = useState(false);
  const [binning, setBinning] = useState<BinningParams>({ mcBin: undefined, eerSampling: undefined });

  const handleParametersChange = useCallback((params: Record<string, unknown>) => {
    setBinning((prev) =>
      prev.mcBin === params.mc_bin && prev.eerSampling === params.eer_sampling
        ? prev
        : { mcBin: params.mc_bin, eerSampling: params.eer_sampling }
    );
  }, []);

  const handleSessionInfoLoaded = useCallback(
    (sessionInfo: Record<string, unknown>, sessionName: string) => {
      setSuperResolution(Boolean(sessionInfo.super_resolution));

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
   * Custom pixel_size field with inline MDOC validation indicator.
   * Replicates the auto-generated renderField behavior (WorkflowLaunchForm.tsx:914-941)
   * but adds dynamic helperText colored by validation state.
   */
  const PixelSizeField = useCallback(
    ({ name, schema: fieldSchema, value, onChange, error }: FormFieldConfig) => {
      const cliFlag = fieldSchema['x-cli-flag'] as string | undefined;
      const label = cliFlag ? `${fieldSchema.title || name} ${cliFlag}` : fieldSchema.title || name;

      // TODO: Switch to SDS IntentMessage when released in @czi-sds/components.
      // Currently using colored helperText as a stand-in for the intent indicator pattern.
      // Ref: https://sds.czi.design/009eaf17b/p/88e8a7-intent
      let helperText: React.ReactNode = error || fieldSchema.description;
      let helperColor: string | undefined;

      if (!error) {
        if (isValidating) {
          helperText = (
            <Box component="span" sx={{ display: 'inline-flex', alignItems: 'center', gap: 0.5 }}>
              <CircularProgress size={12} />
              Verifying pixel size against MDOC file...
            </Box>
          );
          helperColor = 'info.main';
        } else if (pixelSizeValidation.mismatch) {
          helperText = (
            <>
              <strong>Magnification Mismatch</strong> — {pixelSizeValidation.warning}
              {pixelSizeValidation.suggestedPixelSize !== undefined && (
                <>
                  {' '}
                  Expected: <strong>{pixelSizeValidation.suggestedPixelSize} A/px</strong>
                </>
              )}
            </>
          );
          helperColor = 'warning.main';
        } else if (pixelSizeValidation.missing) {
          helperText = (
            <>
              {pixelSizeValidation.warning}
              {pixelSizeValidation.suggestedPixelSize !== undefined && (
                <>
                  {' '}
                  Suggested: <strong>{pixelSizeValidation.suggestedPixelSize} A/px</strong>
                </>
              )}
            </>
          );
          helperColor = 'info.main';
        } else if (pixelSizeValidation.error && pixelSizeValidation.mismatch === undefined) {
          helperText = `Could not verify magnification from MDOC file: ${pixelSizeValidation.error}`;
          helperColor = 'text.secondary';
        }
      }

      // What the tomograms' -AtBin is relative to; shown so the sensor value is not mistaken for it.
      const resolved = resolvedPixelSize(value, superResolution, binning.mcBin, binning.eerSampling);
      const superResStep = superResolution ? ` ÷ ${SUPER_RES_FACTOR}` : '';
      const formula = `${value}${superResStep} × McBin ${binning.mcBin} ÷ EerSampling ${binning.eerSampling}`;
      const resolvedText = resolved === null ? '' : `${resolved.toFixed(PIXEL_SIZE_DECIMALS)} Å/px = ${formula}`;

      return (
        <TextField
          key={name}
          fullWidth
          type="number"
          label={
            <>
              {label}
              <span style={{ color: 'red' }}> *</span>
            </>
          }
          value={value ?? ''}
          onChange={(e) => onChange(parseFloat(e.target.value))}
          helperText={helperText}
          error={Boolean(error)}
          inputProps={{ min: fieldSchema.minimum, max: fieldSchema.maximum, step: 'any' }}
          InputProps={
            resolved === null
              ? undefined
              : {
                  endAdornment: (
                    <InputAdornment position="end">
                      <Tooltip title="Motion-corrected pixel size" subtitle={resolvedText} placement="top">
                        <Button aria-label="About motion-corrected pixel size" sdsStyle="minimal" sdsType="secondary">
                          <Icon sdsIcon="InfoCircle" sdsSize="s" />
                        </Button>
                      </Tooltip>
                    </InputAdornment>
                  ),
                }
          }
          margin="normal"
          sx={{ bgcolor: 'grey.50' }}
          FormHelperTextProps={helperColor && !error ? { sx: { color: helperColor } } : undefined}
        />
      );
    },
    [pixelSizeValidation, isValidating, superResolution, binning]
  );

  /**
   * Additional UI sections specific to AreTomo3 (dose warning only; pixel size moved inline)
   */
  const additionalSections = doseWarning ? (
    <Box key="aretomo3-additional" sx={{ mt: 3 }}>
      <Alert severity="warning" sx={{ mb: 2 }}>
        {doseWarning}
      </Alert>
    </Box>
  ) : null;

  /**
   * Header actions for AreTomo3 - includes CLI import button
   */
  const headerActions = ({ setParameters, schema }: HeaderActionsContext) => (
    <>
      <Button
        sdsType="secondary"
        sdsStyle="outline"
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
      customFields={{ pixel_size: PixelSizeField }}
      additionalSections={additionalSections ? [additionalSections] : undefined}
      headerActions={headerActions}
      onSessionInfoLoaded={handleSessionInfoLoaded}
      onParametersChange={handleParametersChange}
    />
  );
}
