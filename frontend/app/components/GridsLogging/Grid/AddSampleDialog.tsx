'use client';

import React, { useState } from 'react';
import { Box, TextField } from '@mui/material';
import { BaseFormDialog } from '@app/common/components/Forms/BaseFormDialog';
import { disabledTextFieldStyles } from '@app/components/GridsLogging/GridBox/DisableBoxStyle';

interface SampleFormData {
  name: string;
  ontology: string;
}

interface AddSampleDialogProps {
  open: boolean;
  onClose: () => void;
  onSave: (data: SampleFormData) => void;
}

export const AddSampleDialog: React.FC<AddSampleDialogProps> = ({
  open,
  onClose,
  onSave
}) => {
  const [formData, setFormData] = useState<SampleFormData>({
    name: '',
    ontology: ''
  });

  const handleInputChange = (field: keyof SampleFormData, value: string) => {
    setFormData(prev => ({
      ...prev,
      [field]: value
    }));
  };

  const handleSave = () => {
    if (formData.name.trim()) {
      onSave({
        name: formData.name.trim(),
        ontology: formData.ontology.trim()
      });
      // Reset form
      setFormData({
        name: '',
        ontology: ''
      });
      onClose();
    }
  };

  const handleClose = () => {
    // Reset form on close
    setFormData({
      name: '',
      ontology: ''
    });
    onClose();
  };

  return (
    <BaseFormDialog
      open={open}
      onClose={handleClose}
      title="Add New Sample"
      onSave={handleSave}
      disabled={!formData.name.trim()}
    >
      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
        <TextField
          required
          label="Sample Name"
          placeholder="Enter sample name (e.g., lysosome)"
          value={formData.name}
          onChange={(e) => handleInputChange('name', e.target.value)}
          sx={disabledTextFieldStyles}
        />

        <TextField
          label="Ontology"
          placeholder="Enter ontology (e.g., GO:0005764)"
          value={formData.ontology}
          onChange={(e) => handleInputChange('ontology', e.target.value)}
          sx={disabledTextFieldStyles}
        />
      </Box>
    </BaseFormDialog>
  );
};