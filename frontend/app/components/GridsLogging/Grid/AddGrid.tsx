'use client';

import React, { useState, useEffect } from 'react';
import { Box, TextField, InputAdornment, Alert, FormControl, InputLabel, Select, MenuItem } from '@mui/material';
import { disabledTextFieldStyles } from '../GridBox/DisableBoxStyle';
import { BaseFormDialog } from '@app/common/components/Forms/BaseFormDialog';
import { LabelsAutocomplete } from './LabelsAutocomplete';
import { LabelData } from '@app/components/GridsView/components/LabelEditor/LabelChip';
import { DJANGO_URL, POST_API } from '@app/common/constants/api';
import { FormFieldWithAdd } from '@app/common/components/Forms/FormFieldWithAdd';
import { AddSpecimenDialog } from './AddSpecimenDialog';
import { AddProjectDialog } from '@app/components/GridsLogging/Grid/AddProjectDialog';
import { AddFreezingSessionDialog } from '@app/components/GridsLogging/Grid/AddFreezingSessionDialog';
import {
  useGridLoggingChoices,
  useGridLoggingUserList,
  useProjectsList,
  useSpecimenList,
  useFreezingSessionList,
  useCreateGrid,
  useDeviceList,
  useCreateFreezingSession,
  useDocumentationPageList,
  useDriveFolderList,
  useConfluenceSpaceList,
  useProjectLeadersList,
  useGridLoggingGridBoxDetail,
} from '@app/common/hooks/useGridLogging';

import { UserList, FreezingSessionFormData } from '@app/common/types/gridLogging';

interface AddGridProps {
  open: boolean;
  onClose: () => void;
  selectedUser?: UserList | null;
  gridBoxId?: number;
  gridBoxName?: string;
  positionInBox?: number;
  puckId?: number;
  puckName?: string;
  gridBoxPositionInPuck?: number;
  onGridCreated?: (gridPosition: number, gridId: number) => void;
}

export const AddGrid: React.FC<AddGridProps> = ({
  open,
  onClose,
  selectedUser,
  gridBoxId,
  gridBoxName,
  positionInBox,
  puckId,
  gridBoxPositionInPuck,
  onGridCreated,
}) => {
  const { projects, refetch: refetchProjects } = useProjectsList();
  const { transformedSpecimens, isSuccess: specimensLoaded, refetch: refetchSpecimens } = useSpecimenList();
  const [addSpecimenDialogOpen, setAddSpecimenDialogOpen] = useState(false);
  const [addProjectDialogOpen, setAddProjectDialogOpen] = useState(false);
  const [addFreezingSessionDialogOpen, setAddFreezingSessionDialogOpen] = useState(false);
  const [selectedLabels, setSelectedLabels] = useState<LabelData[]>([]);
  const { createGrid, isCreating, error, clearError } = useCreateGrid();
  const { createFreezingSession } = useCreateFreezingSession();
  const { spaces: confluenceSpacesList } = useConfluenceSpaceList();
  const { pages: documentationPagesList, refetch: refetchNotesPages } = useDocumentationPageList();
  const { folders: driveFoldersList } = useDriveFolderList();
  const { projectLeaders: projectLeadersData } = useProjectLeadersList();
  const { isSuccess: choicesLoaded } = useGridLoggingChoices();
  const { users: gridLoggingUsersData, isSuccess: usersLoaded } = useGridLoggingUserList();
  const freezingSessionUsers = gridLoggingUsersData?.users || [];
  const { transformedFreezingSessions, refetch: freezingSessionRefetch } = useFreezingSessionList();
  const { devices: devicesList } = useDeviceList();

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
      setSelectedLabels([]);
    }
  }, [open, selectedUser?.id, positionInBox, gridBoxId, gridBoxName, clearError]);

  const devices = devicesList;
  const projectLeaders =
    (projectLeadersData as { project_leaders?: Array<{ id: number; username: string; full_name: string }> } | undefined)
      ?.project_leaders ?? [];

  const confluenceSpaces = confluenceSpacesList.map((space) => ({
    id: space.id.toString(),
    url: space.url,
  }));

  const googleDriveFolders = driveFoldersList.map((folder) => ({
    id: folder.id.toString(),
    name: folder.name,
  }));

  const notesPages = documentationPagesList;

  // Handle saving a new project
  const handleSaveProject = async (projectId: number) => {
    // Refresh the projects list to include the newly created project
    await refetchProjects?.();
    // Auto-select the newly created project in the form
    setFormData((prev) => ({
      ...prev,
      project: projectId.toString(),
    }));
    setAddProjectDialogOpen(false);
  };

  const handleInputChange = (field: string, value: string | number | boolean) => {
    setFormData((prev) => ({
      ...prev,
      [field]: value,
    }));
  };

  const handleAddSpecimen = async (specimenId: number) => {
    // Refresh the specimens list to include the newly created specimen
    await refetchSpecimens?.();
    // Auto-select the newly created specimen in the form
    setFormData((prev) => ({
      ...prev,
      specimen: specimenId.toString(),
    }));
    setAddSpecimenDialogOpen(false);
  };

  const handleAddFreezingSession = async (data: FreezingSessionFormData) => {
    const result = await createFreezingSession({
      user: Number(data.user),
      device: Number(data.device),
      device_temperature: Number(data.temperature),
      humidity: Number(data.humidity),
      documentation_page: data.notesPage ? Number(data.notesPage) : null,
      freezingSessionDate: data.freezingSessionDate,
    });

    if (result) {
      freezingSessionRefetch?.();
      setFormData((prev) => ({
        ...prev,
        freezingSession: result.id.toString(),
      }));
    }
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
      if (selectedLabels.length > 0) {
        const url = `${DJANGO_URL}${POST_API.UPDATE_GRID_LABELS.replace('grid_id', String(result.id))}`;
        try {
          await fetch(url, {
            method: 'PATCH',
            credentials: 'include',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ label_ids: selectedLabels.map((l) => l.id) }),
          });
        } catch (e) {
          console.error('Failed to update labels:', e);
        }
      }
      onClose();
      if (onGridCreated) {
        onGridCreated(Number(formData.positionInBox), result.id);
      }
    }
  };

  const isFormValid = formData.gridName && formData.specimen && formData.project && formData.positionInBox;
  const { gridBoxData } = useGridLoggingGridBoxDetail(puckId, gridBoxPositionInPuck);
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
              label: specimen.display_name || `Specimen #${specimen.id}`,
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
          {positionInBox !== undefined ? (
            <TextField
              required
              label="Position in Box"
              value={positionInBox}
              disabled
              sx={{ ...disabledTextFieldStyles, flex: 1 }}
            />
          ) : (
            <FormControl required sx={{ flex: 1 }}>
              <InputLabel id="position-label">Position in Box</InputLabel>
              <Select
                labelId="position-label"
                value={formData.positionInBox}
                onChange={(e) => handleInputChange('positionInBox', e.target.value)}
                label="Position in Box"
                sx={disabledTextFieldStyles}
              >
                {gridBoxData?.grid_box?.positions?.map((position) => (
                  <MenuItem key={position.q} value={position.q} disabled={position.occupied}>
                    Position {position.q} {position.occupied ? '(Filled)' : '(Available)'}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          )}

          <TextField
            required
            label="Grid Box"
            value={formData.gridBoxName}
            disabled
            sx={{ ...disabledTextFieldStyles, flex: 1 }}
          />
        </Box>

        <TextField
          label="Notes"
          placeholder="Add notes..."
          value={formData.notes}
          onChange={(e) => handleInputChange('notes', e.target.value)}
          multiline
          rows={3}
          sx={{ ...disabledTextFieldStyles, flex: 1 }}
        />

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

        <LabelsAutocomplete value={selectedLabels} onChange={setSelectedLabels} sx={disabledTextFieldStyles} />
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
        users={freezingSessionUsers}
        devices={devices}
        notesPages={notesPages}
        onSave={handleAddFreezingSession}
        refetchNotesPages={refetchNotesPages}
      />
    </>
  );
};
