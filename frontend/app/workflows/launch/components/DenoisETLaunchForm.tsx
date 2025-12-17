'use client';

/**
 * DenoisETLaunchForm - Processor-specific launch form for DenoisET
 *
 * Extends the base WorkflowLaunchForm with DenoisET-specific features:
 * - Selection of AreTomo3 runs to denoise
 * - Model selection and configuration
 * - Patch size and stride validation
 */

import { Box } from '@mui/material';
import type { ValidationError, WorkflowLaunchFormProps } from '@app/common/types/workflow';
import WorkflowLaunchForm from './WorkflowLaunchForm';

interface DenoisETLaunchFormProps
  extends Omit<WorkflowLaunchFormProps, 'customFields' | 'additionalSections' | 'customValidation'> {
  // No additional props needed for now
}

export default function DenoisETLaunchForm(props: DenoisETLaunchFormProps) {
  /**
   * Custom validation for DenoisET parameters
   *
   * NOTE: This validation is SUPPLEMENTARY to automatic JSON schema validation.
   * The schema (denoiset/schema.yaml) already validates:
   * - Required fields (aretomo_run, model_name)
   * - Field types and enums (model_name options)
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

    // Validate aretomo_run selection
    if (!parameters.aretomo_run) {
      errors.push({
        field: 'aretomo_run',
        message: 'Please select an AreTomo3 run to denoise',
      });
    }

    // Validate patch size if provided
    if (parameters.patch_size) {
      const patchSize = parseInt(String(parameters.patch_size));
      if (patchSize < 32 || patchSize > 512) {
        errors.push({
          field: 'patch_size',
          message: 'Patch size must be between 32 and 512 pixels',
        });
      }
      // Patch size should be a multiple of 8 for optimal GPU performance
      if (patchSize % 8 !== 0) {
        errors.push({
          field: 'patch_size',
          message: 'Patch size should be a multiple of 8 for optimal GPU performance',
        });
      }
    }

    // Validate stride if provided
    if (parameters.stride && parameters.patch_size) {
      const stride = parseInt(String(parameters.stride));
      const patchSize = parseInt(String(parameters.patch_size));

      if (stride <= 0) {
        errors.push({
          field: 'stride',
          message: 'Stride must be greater than 0',
        });
      }

      if (stride > patchSize) {
        errors.push({
          field: 'stride',
          message: 'Stride cannot be larger than patch size',
        });
      }
    }

    // Validate model selection
    if (!parameters.model_name) {
      errors.push({
        field: 'model_name',
        message: 'Please select a denoising model',
      });
    }

    return errors;
  };

  /**
   * Additional UI sections specific to DenoisET
   */
  const additionalSections = (
    <Box key="denoiset-additional" sx={{ mt: 3 }}>
      {/*/!* DenoisET-specific help *!/*/}
      {/*<Alert severity="info" sx={{ mb: 2 }}>*/}
      {/*  <Typography variant="subtitle2" gutterBottom>*/}
      {/*    DenoisET Processing Tips*/}
      {/*  </Typography>*/}
      {/*  <ul style={{ margin: 0, paddingLeft: '20px' }}>*/}
      {/*    <li>*/}
      {/*      TODO: Put some helpful tips here.*/}
      {/*    </li>*/}
      {/*  </ul>*/}
      {/*</Alert>*/}
    </Box>
  );

  return (
    <WorkflowLaunchForm {...props} customValidation={customValidation} additionalSections={[additionalSections]} />
  );
}
