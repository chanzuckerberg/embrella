'use client';

import React, { useState } from 'react';
import { Box, TextField } from '@mui/material';
import { UsersList } from '@app/common/types/gridLogging/userList';
import { useGridLoggingChoices } from '@app/common/hooks/useGridLogging/useGridLoggingChoices';
import { useGridLoggingUserList } from '@app/common/hooks/useGridLogging/useGridLoggingUserList';
import { disabledTextFieldStyles } from '../GridBox/DisableBoxStyle';
import { BaseFormDialog } from '@app/common/components/Forms/BaseFormDialog';
import { FormFieldWithAdd } from '@app/common/components/Forms/FormFieldWithAdd';
import { AddItemDialog } from '@app/common/components/Forms/AddItemDialog';

interface AddGridProps {
  open: boolean;
  onClose: () => void;
  selectedUser?: UsersList | null;
  gridBoxId?: number;
  gridBoxName?: string;
  positionInBox?: number;
  puckId?: number;
  puckName?: string;
}

export const AddGrid: React.FC<AddGridProps> = ({
  open,
  onClose,
  selectedUser,
  gridBoxId,
  gridBoxName,
  positionInBox,
}) => {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [addSpecimenDialogOpen, setAddSpecimenDialogOpen] = useState(false);
  const [addProjectDialogOpen, setAddProjectDialogOpen] = useState(false);
  const [addFreezingSessionDialogOpen, setAddFreezingSessionDialogOpen] = useState(false);
  
  const [formData, setFormData] = useState({
    user: selectedUser?.id || '',
    gridName: '',
    freezingSession: '',
    specimen: '',
    project: '',
    positionInBox: positionInBox || '',
    gridBox: gridBoxId || '',
    gridBoxName: gridBoxName || '',
    notes: '',
    clipped: false,
    blotTime: '',
    blotForce: '',
    blotDistance: '',
  });

  const { choices, isSuccess: choicesLoaded } = useGridLoggingChoices();
  const { users, isSuccess: usersLoaded } = useGridLoggingUserList();

  const handleInputChange = (field: string, value: string | number | boolean) => {
    setFormData((prev) => ({
      ...prev,
      [field]: value,
    }));
  };

  const handleAddSpecimen = (specimenName: string) => {
    console.log('Adding new specimen:', specimenName);
  };

  const handleAddProject = (projectName: string) => {
    console.log('Adding new project:', projectName);
  };

  const handleAddFreezingSession = (sessionName: string) => {
    console.log('Adding new freezing session:', sessionName);
  };

  const handleSave = () => {
    if (
      !formData.user ||
      !formData.gridName ||
      !formData.specimen ||
      !formData.project ||
      !formData.positionInBox ||
      !formData.gridBox
    ) {
      alert('Please fill in all required fields');
      return;
    }

    setIsSubmitting(true);
    console.log('Saving grid:', formData);
  };

  return (
    <>
      <BaseFormDialog
        open={open}
        onClose={onClose}
        title="Add a Grid"
        subtitle={selectedUser?.full_name || ''}
        onSave={handleSave}
        isSubmitting={isSubmitting}
        disabled={!choicesLoaded || !usersLoaded}
      >
        <Box sx={{ display: 'flex', gap: 2, alignItems: 'flex-start' }}>
          <TextField
            required
            label="Grid Name"
            placeholder="Grid Name [Ex.Grid1]"
            value={formData.gridName}
            onChange={(e) => handleInputChange('gridName', e.target.value)}
            sx={{ ...disabledTextFieldStyles, flex: 1 }}
          />
          <FormFieldWithAdd
            label="Freezing Session"
            value={formData.freezingSession}
            onChange={(value) => handleInputChange('freezingSession', value)}
            onAdd={() => setAddFreezingSessionDialogOpen(true)}
            disabled={!choicesLoaded}
            options={choices?.freezing_sessions || []}
          />
        </Box>

        <Box sx={{ display: 'flex', gap: 2, alignItems: 'flex-start' }}>
          <FormFieldWithAdd
            label="Specimen"
            value={formData.specimen}
            onChange={(value) => handleInputChange('specimen', value)}
            onAdd={() => setAddSpecimenDialogOpen(true)}
            required
            disabled={!choicesLoaded}
            options={choices?.specimens || []}
          />
          <FormFieldWithAdd
            label="Project"
            value={formData.project}
            onChange={(value) => handleInputChange('project', value)}
            onAdd={() => setAddProjectDialogOpen(true)}
            required
            disabled={!choicesLoaded}
            options={choices?.projects || []}
          />
        </Box>

        <Box sx={{ display: 'flex', gap: 2 }}>
          <TextField
            required
            label="Position in box"
            value={formData.positionInBox}
            disabled
            sx={{ ...disabledTextFieldStyles, flex: 1 }}
          />
          <TextField
            required
            label="Grid Box"
            value={formData.gridBoxName}
            disabled
            sx={{ ...disabledTextFieldStyles, flex: 1 }}
          />
        </Box>

        <Box sx={{ display: 'flex', gap: 2 }}>
          <TextField
            label="Notes"
            placeholder="Add notes..."
            value={formData.notes}
            onChange={(e) => handleInputChange('notes', e.target.value)}
            multiline
            rows={3}
            sx={{ ...disabledTextFieldStyles, flex: 1 }}
          />
        </Box>

        <Box sx={{ display: 'flex', gap: 2 }}>
          <TextField
            label="Blot Time"
            value={formData.blotTime}
            onChange={(e) => handleInputChange('blotTime', e.target.value)}
            sx={{ ...disabledTextFieldStyles, flex: 1 }}
          />
          <TextField
            label="Blot Force"
            value={formData.blotForce}
            onChange={(e) => handleInputChange('blotForce', e.target.value)}
            sx={{ ...disabledTextFieldStyles, flex: 1 }}
          />
          <TextField
            label="Blot Distance"
            value={formData.blotDistance}
            onChange={(e) => handleInputChange('blotDistance', e.target.value)}
            sx={{ ...disabledTextFieldStyles, flex: 1 }}
          />
        </Box>
      </BaseFormDialog>

      <AddItemDialog
        open={addSpecimenDialogOpen}
        onClose={() => setAddSpecimenDialogOpen(false)}
        title="Add New Specimen"
        fieldLabel="Specimen Name"
        fieldPlaceholder="Enter specimen name"
        onSave={handleAddSpecimen}
      />

      <AddItemDialog
        open={addProjectDialogOpen}
        onClose={() => setAddProjectDialogOpen(false)}
        title="Add New Project"
        fieldLabel="Project Name"
        fieldPlaceholder="Enter project name"
        onSave={handleAddProject}
      />

      <AddItemDialog
        open={addFreezingSessionDialogOpen}
        onClose={() => setAddFreezingSessionDialogOpen(false)}
        title="Add New Freezing Session"
        fieldLabel="Freezing Session Name"
        fieldPlaceholder="Enter freezing session name"
        onSave={handleAddFreezingSession}
      />
    </>
  );
};