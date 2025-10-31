'use client';

import React, { useState } from 'react';
import { Box, TextField } from '@mui/material';
import { BaseFormDialog } from '@app/common/components/Forms/BaseFormDialog';
import { disabledTextFieldStyles } from '@app/components/GridsLogging/GridBox/DisableBoxStyle';
import { FormFieldWithAdd } from '@app/common/components/Forms/FormFieldWithAdd';
import { AddSampleDialog } from './AddSampleDialog';

interface SpecimenFormData {
  sampleName: string;
  notesPage: string;
  notes: string;
}

interface AddSpecimenDialogProps {
  open: boolean;
  onClose: () => void;
  onSave: (data: SpecimenFormData) => void;
}

export const AddSpecimenDialog: React.FC<AddSpecimenDialogProps> = ({ open, onClose, onSave }) => {
  const [formData, setFormData] = useState<SpecimenFormData>({
    sampleName: '',
    notesPage: '',
    notes: '',
  });

  const [addSampleDialogOpen, setAddSampleDialogOpen] = useState(false);

  const handleInputChange = (field: keyof SpecimenFormData, value: string) => {
    setFormData((prev) => ({
      ...prev,
      [field]: value,
    }));
  };

  const handleAddSample = (sampleData: { name: string; ontology: string }) => {
    setFormData((prev) => ({
      ...prev,
      sampleName: sampleData.name, // or the ID returned from API
    }));
  };
  const handleSave = () => {
    if (formData.sampleName.trim()) {
      onSave({
        sampleName: formData.sampleName.trim(),
        notesPage: formData.notesPage.trim(),
        notes: formData.notes.trim(),
      });
      // Reset form
      setFormData({
        sampleName: '',
        notesPage: '',
        notes: '',
      });
      onClose();
    }
  };

  const handleClose = () => {
    // Reset form on close
    setFormData({
      sampleName: '',
      notesPage: '',
      notes: '',
    });
    onClose();
  };

  return (
    <>
      <BaseFormDialog
        open={open}
        onClose={handleClose}
        title="Add New Specimen"
        onSave={handleSave}
        disabled={!formData.sampleName.trim()}
      >
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
          <FormFieldWithAdd
            label="Sample Name"
            value={formData.sampleName}
            onChange={(value) => handleInputChange('sampleName', value)}
            onAdd={() => setAddSampleDialogOpen(true)}
            required
            // options={existingSamples}
            placeholder="Select or add sample name"
          />

          <TextField
            label="Notes Page"
            placeholder="Enter notes page (e.g., https://confluence.example.com/display/GRID/Sample+Prep)"
            value={formData.notesPage}
            onChange={(e) => handleInputChange('notesPage', e.target.value)}
            sx={disabledTextFieldStyles}
          />

          <TextField
            label="Notes"
            placeholder="Add notes about specimen preparation..."
            value={formData.notes}
            onChange={(e) => handleInputChange('notes', e.target.value)}
            multiline
            rows={3}
            sx={disabledTextFieldStyles}
          />
        </Box>
      </BaseFormDialog>

      {/* Nested dialog for adding new sample */}
      <AddSampleDialog
        open={addSampleDialogOpen}
        onClose={() => setAddSampleDialogOpen(false)}
        onSave={handleAddSample}
      />
    </>
  );
};
