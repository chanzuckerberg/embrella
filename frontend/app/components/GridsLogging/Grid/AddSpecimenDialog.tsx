'use client';

import React, { useState, useEffect } from 'react';
import { Box, TextField, Alert } from '@mui/material';
import { BaseFormDialog } from '@app/common/components/Forms/BaseFormDialog';
import { disabledTextFieldStyles } from '@app/components/GridsLogging/GridBox/DisableBoxStyle';
import { AddSampleDialog } from './AddSampleDialog';
import { SamplesAutocomplete } from './SamplesAutocomplete';
import { Sample } from '@app/common/types/gridLogging';
import { useCreateSpecimen, useSampleList } from '@app/common/hooks/useGridLogging';

interface SpecimenFormData {
  samples: Sample[];
  notesPage: string;
  notes: string;
}

interface AddSpecimenDialogProps {
  open: boolean;
  onClose: () => void;
  onSave?: (specimenId: number) => void;
}

const INITIAL_FORM: SpecimenFormData = {
  samples: [],
  notesPage: '',
  notes: '',
};

export const AddSpecimenDialog: React.FC<AddSpecimenDialogProps> = ({ open, onClose, onSave }) => {
  const [formData, setFormData] = useState<SpecimenFormData>(INITIAL_FORM);
  const [addSampleDialogOpen, setAddSampleDialogOpen] = useState(false);
  const { createSpecimen, isCreating, error, clearError } = useCreateSpecimen();
  const { refetch: refetchSamples } = useSampleList();

  useEffect(() => {
    if (!open) {
      clearError();
    }
  }, [open, clearError]);

  const handleAddSample = (sampleId: number, sampleName: string) => {
    refetchSamples?.();
    setFormData((prev) =>
      prev.samples.some((s) => s.id === sampleId)
        ? prev
        : { ...prev, samples: [...prev.samples, { id: sampleId, name: sampleName, ontology: '' }] }
    );
  };

  const handleSave = async () => {
    if (formData.samples.length === 0) return;
    const result = await createSpecimen({
      sample_ids: formData.samples.map((s) => s.id),
      notes: formData.notes.trim() || undefined,
      notes_page: formData.notesPage.trim() ? parseInt(formData.notesPage) : undefined,
    });

    if (result) {
      if (onSave) {
        onSave(result.specimen.id);
      }
      setFormData(INITIAL_FORM);
      onClose();
    }
  };

  const handleClose = () => {
    setFormData(INITIAL_FORM);
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
        disabled={formData.samples.length === 0 || isCreating}
        saveButtonText={isCreating ? 'Creating...' : 'Save'}
      >
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
          {Boolean(error) && (
            <Alert severity="error" onClose={clearError}>
              {error}
            </Alert>
          )}
          <label style={{ fontSize: '12px', color: 'grey' }}>Samples Present on Grid</label>
          <SamplesAutocomplete
            value={formData.samples}
            onChange={(samples) => setFormData((prev) => ({ ...prev, samples }))}
            onAddNew={() => setAddSampleDialogOpen(true)}
            disabled={isCreating}
            required
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
