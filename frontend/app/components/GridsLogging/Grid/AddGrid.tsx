'use client';

import React, { useState } from 'react';
import { Box, TextField } from '@mui/material';
import { UsersList } from '@app/common/types/gridLogging/userList';
import { useGridLoggingChoices } from '@app/common/hooks/useGridLogging/useGridLoggingChoices';
import { useGridLoggingUserList } from '@app/common/hooks/useGridLogging/useGridLoggingUserList';
import { disabledTextFieldStyles } from '../GridBox/DisableBoxStyle';
import { BaseFormDialog } from '@app/common/components/Forms/BaseFormDialog';
import { FormFieldWithAdd } from '@app/common/components/Forms/FormFieldWithAdd';
import { AddSpecimenDialog } from './AddSpecimenDialog';
import { AddProjectDialog } from '@app/components/GridsLogging/Grid/AddProjectDialog';
import { AddFreezingSessionDialog } from '@app/components/GridsLogging/Grid/AddFreezingSessionDialog';
import { useProjectsList } from '@app/common/hooks/useGridLogging/useProjectList';

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
  // Fetch projects list
  const { projects, isSuccess: projectsLoaded } = useProjectsList();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [addSpecimenDialogOpen, setAddSpecimenDialogOpen] = useState(false);
  const [addProjectDialogOpen, setAddProjectDialogOpen] = useState(false);
  const [addFreezingSessionDialogOpen, setAddFreezingSessionDialogOpen] = useState(false);

  const [formData, setFormData] = useState({
    user: selectedUser?.id || '',
    gridName: 'Grid-',
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

  const projectLeaders =
    users?.users?.map((user) => ({
      id: user.id.toString(),
      name: user.full_name,
    })) || [];

  const confluenceSpaces = [{ id: '1', url: 'https://czbiohub.atlassian.net/wiki/spaces/CHOL/overview' }];

  const googleDriveFolders = [
    { id: '1', name: 'BD01' },
    { id: '2', name: 'Phantom 2' },
  ];

  const devices = [
    { id: '1', name: 'GP2' },
    { id: '2', name: 'Vitrobot' },
    { id: '3', name: 'Leica EM Ice [High Pressure Freezing]' },
    { id: '4', name: 'CryoCapCell' },
  ];

  const notesPages = [
    { id: '1', url: 'VLP Freezing' },
    { id: '1', url: 'Sample Prep Notes' },
  ];

  const handleSaveProject = async (data: {
    name: string;
    description: string;
    projectLeader: string;
    confluenceSpace: string;
    googleDriveFolder: string;
  }) => {
    console.log('Saving project:', data);

    setFormData((prev) => ({
      ...prev,
      project: data.name,
    }));
  };

  const handleInputChange = (field: string, value: string | number | boolean) => {
    setFormData((prev) => ({
      ...prev,
      [field]: value,
    }));
  };

  const handleAddSpecimen = (specimenData: { sampleName: string; notesPage: string; notes: string }) => {
    console.log('Adding new specimen:', specimenData);
  };

  const handleAddFreezingSession = async (data: {
    user: string;
    device: string;
    name: string;
    temperature: string;
    humidity: string;
    notesPage: string;
  }) => {
    console.log('Adding new freezing session:', data);

    setFormData((prev) => ({
      ...prev,
      freezingSession: data.name,
    }));
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
            // options={choices?.freezing_sessions || []}
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
            // options={choices?.specimens || []}
          />
          <FormFieldWithAdd
            label="Project"
            value={formData.project}
            onChange={(value) => handleInputChange('project', value)}
            onAdd={() => setAddProjectDialogOpen(true)}
            required
            disabled={!choicesLoaded}
            options={projects.map((project) => ({
              value: project.id.toString(),
              label: project.name,
            }))}
          />
        </Box>

        <Box sx={{ display: 'flex', gap: 2 }}>
          <TextField
            required
            label="Position in box"
            value={positionInBox}
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

      <AddSpecimenDialog
        open={addSpecimenDialogOpen}
        onClose={() => setAddSpecimenDialogOpen(false)}
        onSave={handleAddSpecimen}
      />

      <AddProjectDialog
        open={addProjectDialogOpen}
        onClose={() => setAddProjectDialogOpen(false)}
        onSave={handleSaveProject}
        projectLeaders={projectLeaders}
        confluenceSpaces={confluenceSpaces}
        googleDriveFolders={googleDriveFolders}
      />

      <AddFreezingSessionDialog
        open={addFreezingSessionDialogOpen}
        onClose={() => setAddFreezingSessionDialogOpen(false)}
        users={projectLeaders}
        devices={devices}
        notesPages={notesPages}
        onSave={handleAddFreezingSession}
      />
    </>
  );
};
