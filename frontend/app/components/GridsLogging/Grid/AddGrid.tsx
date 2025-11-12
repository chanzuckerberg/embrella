'use client';

import React, { useState, useEffect } from 'react';
import { Box, TextField, InputAdornment, Alert } from '@mui/material';
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
import { useSpecimenList } from '@app/common/hooks/useGridLogging/useSpecimenList';
import { useFreezingSessionList } from '@app/common/hooks/useGridLogging/useFreezingSessionList';
import { useCreateGrid } from '@app/common/hooks/useGridLogging/useCreateGrid';
import { useDeviceList } from '@app/common/hooks/useGridLogging/useDeviceList';

interface AddGridProps {
  open: boolean;
  onClose: () => void;
  selectedUser?: UsersList | null;
  gridBoxId?: number;
  gridBoxName?: string;
  positionInBox?: number;
  puckId?: number;
  puckName?: string;
  onGridCreated?: (gridPosition: number, gridId: number) => void;
}

export const AddGrid: React.FC<AddGridProps> = ({
  open,
  onClose,
  selectedUser,
  gridBoxId,
  gridBoxName,
  positionInBox,
  onGridCreated,
}) => {
  // Fetch projects list
  const { projects } = useProjectsList();
  const [addSpecimenDialogOpen, setAddSpecimenDialogOpen] = useState(false);
  const [addProjectDialogOpen, setAddProjectDialogOpen] = useState(false);
  const [addFreezingSessionDialogOpen, setAddFreezingSessionDialogOpen] = useState(false);
  const { createGrid, isCreating, error, clearError } = useCreateGrid();

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

  // Reset form when dialog opens
  useEffect(() => {
    if (open) {
      setFormData({
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
      clearError();
    }
  }, [open, selectedUser?.id, positionInBox, gridBoxId, gridBoxName]);

  const { isSuccess: choicesLoaded } = useGridLoggingChoices();
  const { users, isSuccess: usersLoaded } = useGridLoggingUserList();
  const { transformedSpecimens, isSuccess: specimensLoaded } = useSpecimenList();
  const { transformedFreezingSessions } = useFreezingSessionList();
  const { devices: devicesList, isSuccess: devicesLoaded } = useDeviceList();

  // Transform devices to match the expected interface
  const devices = devicesList.map(device => ({
    id: device.id.toString(),  // Convert number to string
    name: device.name,
  }));
  
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
    temperature: string;
    humidity: string;
    notesPage: string;
  }) => {

  };

  const handleSave = async () => {
    if (!formData.gridName || !formData.specimen || !formData.project || !formData.positionInBox || !gridBoxId) {
      alert('Please fill in all required fields');
      return;
    }
  
    const result = await createGrid({
      name: formData.gridName,
      user: Number(formData.user),
      specimen: Number(formData.specimen),
      intended_project: Number(formData.project),
      grid_box: Number(gridBoxId),
      position_in_box: Number(formData.positionInBox),
      ...(formData.freezingSession && { freezing_session: Number(formData.freezingSession) }),
      ...(formData.notes && { notes: formData.notes }),
      clipped: formData.clipped,
      ...(formData.blotTime && { blot_time: Number(formData.blotTime) }),
      ...(formData.blotForce && { blot_force: Number(formData.blotForce) }),
      ...(formData.blotDistance && { blot_distance: Number(formData.blotDistance) }),
    });
  
    if (result) {
      onClose();
      if (onGridCreated) {
        onGridCreated(Number(formData.positionInBox), result.id);
      }
    }
  };

  const isFormValid = formData.gridName && formData.specimen && formData.project && formData.positionInBox;
  return (
    <>
      <BaseFormDialog
        open={open}
        onClose={onClose}
        title="Add a Grid"
        subtitle={selectedUser?.full_name || ''}
        onSave={handleSave}
        isSubmitting={isCreating}
        disabled={!choicesLoaded || !usersLoaded || !isFormValid}
      >
         {Boolean(error) && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
          )}
        <Box sx={{ display: 'flex', gap: 2, alignItems: 'flex-start' }}>
          <TextField
            required
            label="Grid Name"
            placeholder="Grid Name [Ex.Grid1]"
            value={formData.gridName}
            onChange={(e) => handleInputChange('gridName', e.target.value)}
            InputProps={{
              startAdornment: (
                <InputAdornment position="start" sx={{ color: 'rgba(0, 0, 0, 0.87)', mr: -4 }}>
                  Grid-
                </InputAdornment>
              ),
            }}
            sx={{
              ...disabledTextFieldStyles,
              flex: 1,
              '& .MuiInputBase-input': { paddingLeft: 0 },
            }}
          />
          <FormFieldWithAdd
            label="Freezing Session"
            value={formData.freezingSession}
            onChange={(value) => handleInputChange('freezingSession', value)}
            onAdd={() => setAddFreezingSessionDialogOpen(true)}
            disabled={!choicesLoaded}
            options={transformedFreezingSessions.map((freezingSession) => ({
              value: freezingSession.id.toString(),
              label: freezingSession.display_name,
            }))}
          
          />
        </Box>

        <Box sx={{ display: 'flex', gap: 2, alignItems: 'flex-start' }}>
          <FormFieldWithAdd
            label="Specimen"
            value={formData.specimen}
            onChange={(value) => handleInputChange('specimen', value)}
            onAdd={() => setAddSpecimenDialogOpen(true)}
            required
            disabled={!choicesLoaded || !specimensLoaded}
            options={transformedSpecimens.map((specimen) => ({
              value: specimen.id.toString(),
              label: specimen.display_name,
            }))}
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