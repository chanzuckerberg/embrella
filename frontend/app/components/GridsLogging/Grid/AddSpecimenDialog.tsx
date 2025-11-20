'use client';

import React, { useState, useEffect } from 'react';
import { Box, TextField, Alert } from '@mui/material';
import { BaseFormDialog } from '@app/common/components/Forms/BaseFormDialog';
import { disabledTextFieldStyles } from '@app/components/GridsLogging/GridBox/DisableBoxStyle';
import { FormFieldWithAdd } from '@app/common/components/Forms/FormFieldWithAdd';
import { AddSampleDialog } from './AddSampleDialog';
import { useSampleList, useCreateSpecimen } from '@app/common/hooks/useGridLogging';

interface SpecimenFormData {
  sampleIds: number[];
  notesPage: string;
  notes: string;
}

interface AddSpecimenDialogProps {
  open: boolean;
  onClose: () => void;
  onSave?: (specimenId: number) => void;
}

export const AddSpecimenDialog: React.FC<AddSpecimenDialogProps> = ({ open, onClose, onSave }) => {
  const [formData, setFormData] = useState<SpecimenFormData>({
    sampleIds: [],
    notesPage: '',
    notes: '',
  });

  const [addSampleDialogOpen, setAddSampleDialogOpen] = useState(false);
  const { transformedSamples, refetch } = useSampleList();
  const { createSpecimen, isCreating, error, clearError } = useCreateSpecimen();

  useEffect(() => {
    if (!open) {
      clearError();
    }
  }, [open, clearError]);

  const handleSampleChange = (value: string) => {
    const sampleId = parseInt(value);
    if (!isNaN(sampleId)) {
      setFormData((prev) => ({
        ...prev,
        sampleIds: [sampleId],
      }));
    }
  };

  const handleAddSample = (sampleId: number, _sampleName: string) => {
    // Refresh the samples list to include the newly created sample
    refetch?.();
    // Auto-select the newly created sample
    setFormData((prev) => ({
      ...prev,
      sampleIds: [sampleId],
    }));
  };

  const handleSave = async () => {
    if (formData.sampleIds.length > 0) {
      const result = await createSpecimen({
        sample_ids: formData.sampleIds,
        notes: formData.notes.trim() || undefined,
        notes_page: formData.notesPage.trim() ? parseInt(formData.notesPage) : undefined,
      });

      if (result) {
        if (onSave) {
          onSave(result.specimen.id);
        }
        setFormData({
          sampleIds: [],
          notesPage: '',
          notes: '',
        });
        onClose();
      }
    }
  };

  const handleClose = () => {
    // Reset form on close
    setFormData({
      sampleIds: [],
      notesPage: '',
      notes: '',
    });
    clearError();
    onClose();
  };

  return (
    <>
      <BaseFormDialog
        open={open}
        onClose={handleClose}
        title="Add New Specimen"
        onSave={handleSave}
        disabled={formData.sampleIds.length === 0 || isCreating}
        saveButtonText={isCreating ? 'Creating...' : 'Save'}
      >
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
          {Boolean(error) && (
            <Alert severity="error" onClose={clearError}>
              {error}
            </Alert>
          )}

          <FormFieldWithAdd
            label="Sample Name:Combination of samples on a grid"
            value={formData.sampleIds[0]?.toString() || ''}
            onChange={handleSampleChange}
            onAdd={() => setAddSampleDialogOpen(true)}
            required
            options={transformedSamples.map((sample) => ({
              value: sample.id.toString(),
              label: sample.label,
            }))}
            placeholder="Select or add sample name"
            disabled={isCreating}
          />

          <TextField
            label="Notes Page ID"
            placeholder="Enter Confluence page ID (optional)"
            value={formData.notesPage}
            onChange={(e) => setFormData((prev) => ({ ...prev, notesPage: e.target.value }))}
            sx={disabledTextFieldStyles}
            disabled={isCreating}
            type="number"
          />

          <TextField
            label="Notes"
            placeholder="Add notes about specimen preparation..."
            value={formData.notes}
            onChange={(e) => setFormData((prev) => ({ ...prev, notes: e.target.value }))}
            multiline
            rows={3}
            sx={disabledTextFieldStyles}
            disabled={isCreating}
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
