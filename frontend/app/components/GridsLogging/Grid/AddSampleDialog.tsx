'use client';

import React, { useState, useEffect } from 'react';
import { Box, TextField, Alert } from '@mui/material';
import { BaseFormDialog } from '@app/common/components/Forms/BaseFormDialog';
import { disabledTextFieldStyles } from '@app/components/GridsLogging/GridBox/DisableBoxStyle';
import { useCreateSample } from '@app/common/hooks/useGridLogging';

interface SampleFormData {
  name: string;
  ontology: string;
}

interface AddSampleDialogProps {
  open: boolean;
  onClose: () => void;
  onSave?: (sampleId: number, sampleName: string) => void;
}

export const AddSampleDialog: React.FC<AddSampleDialogProps> = ({ open, onClose, onSave }) => {
  const [formData, setFormData] = useState<SampleFormData>({
    name: '',
    ontology: '',
  });

  const { createSample, isCreating, error, clearError } = useCreateSample();

  useEffect(() => {
    if (!open) {
      clearError();
    }
  }, [open, clearError]);

  const handleInputChange = (field: keyof SampleFormData, value: string) => {
    setFormData((prev) => ({
      ...prev,
      [field]: value,
    }));
  };

  const handleSave = async () => {
    if (formData.name.trim()) {
      const result = await createSample({
        name: formData.name.trim(),
        ontology: formData.ontology.trim(),
      });

      if (result) {
        if (onSave) {
          onSave(result.sample.id, result.sample.name);
        }
        setFormData({
          name: '',
          ontology: '',
        });
        onClose();
      }
    }
  };

  const handleClose = () => {
    // Reset form on close
    setFormData({
      name: '',
      ontology: '',
    });
    clearError();
    onClose();
  };

  return (
    <BaseFormDialog
      open={open}
      onClose={handleClose}
      title="Add New Sample"
      onSave={handleSave}
      disabled={!formData.name.trim() || isCreating}
      saveButtonText={isCreating ? 'Creating...' : 'Save'}
    >
      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
        {Boolean(error) && (
          <Alert severity="error" onClose={clearError}>
            {error}
          </Alert>
        )}

        <TextField
          required
          label="An individual sample (e.g., apoferritin)"
          placeholder="Enter sample name (e.g., lysosome)"
          value={formData.name}
          onChange={(e) => handleInputChange('name', e.target.value)}
          sx={disabledTextFieldStyles}
          disabled={isCreating}
        />

        <TextField
          label="Ontology: Sample should have an ontology identifier"
          placeholder="Enter ontology (e.g., GO:0005764)"
          value={formData.ontology}
          onChange={(e) => handleInputChange('ontology', e.target.value)}
          sx={disabledTextFieldStyles}
          disabled={isCreating}
        />
      </Box>
    </BaseFormDialog>
  );
};
