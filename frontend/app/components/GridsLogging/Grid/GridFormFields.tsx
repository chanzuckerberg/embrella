'use client';

import React from 'react';
import { Box, TextField, Checkbox, FormControlLabel, MenuItem } from '@mui/material';
import { disabledTextFieldStyles } from '@app/components/GridsLogging/GridBox/DisableBoxStyle';
import { LabelsAutocomplete } from '@app/components/GridsLogging/Grid/LabelsAutocomplete';
import { LabelData } from '@app/components/GridsView/components/LabelEditor/LabelChip';
import { FreezingSession } from '@app/common/types/gridLogging/entities/freezingSessionList';
import { Specimen } from '@app/common/types/gridLogging/entities/specimenList';
import { ProjectData } from '@app/common/types/gridLogging/entities/projectList';
import { EditedData, GridFormData } from './utils';

interface GridFormFieldsProps {
  formData: GridFormData;
  editedData: EditedData;
  isEditMode: boolean;
  onFieldChange: (field: keyof EditedData, value: string | number | null) => void;
  clippedValue: boolean;
  trashedValue: boolean;
  onClippedChange: (event: React.ChangeEvent<HTMLInputElement>) => void;
  onTrashedChange: (event: React.ChangeEvent<HTMLInputElement>) => void;
  currentLabels: LabelData[];
  onLabelsChange: (labels: LabelData[]) => void;
  freezingSessions: FreezingSession[] | undefined;
  specimens: Specimen[] | undefined;
  projects: ProjectData[] | undefined;
}

export const GridFormFields: React.FC<GridFormFieldsProps> = ({
  formData,
  editedData,
  isEditMode,
  onFieldChange,
  clippedValue,
  trashedValue,
  onClippedChange,
  onTrashedChange,
  currentLabels,
  onLabelsChange,
  freezingSessions,
  specimens,
  projects,
}) => (
  <>
    <Box sx={{ display: 'flex', gap: 2 }}>
      <TextField
        fullWidth
        label="Grid Name"
        disabled={!isEditMode}
        value={isEditMode ? editedData.gridName : formData.gridName}
        onChange={(e) => onFieldChange('gridName', e.target.value)}
        sx={!isEditMode ? disabledTextFieldStyles : { mb: 5 }}
      />
      <TextField
        fullWidth
        label="Copy Number"
        disabled={!isEditMode}
        value={isEditMode ? editedData.copyNumber : formData.copyNumber}
        onChange={(e) => onFieldChange('copyNumber', parseInt(e.target.value) || 1)}
        type="number"
        sx={!isEditMode ? disabledTextFieldStyles : { mb: 5 }}
      />
      <TextField fullWidth label="User" disabled value={formData.user} sx={disabledTextFieldStyles} />
    </Box>

    <Box sx={{ display: 'flex', gap: 2 }}>
      <TextField
        fullWidth
        label="Notes"
        disabled={!isEditMode}
        value={isEditMode ? editedData.notes : formData.notes}
        onChange={(e) => onFieldChange('notes', e.target.value)}
        multiline
        rows={1}
        sx={!isEditMode ? disabledTextFieldStyles : { mb: 5 }}
      />
      <FormControlLabel
        control={<Checkbox checked={clippedValue} onChange={onClippedChange} color="primary" />}
        label="Clipped"
      />
      <FormControlLabel
        control={
          <Checkbox
            checked={trashedValue}
            onChange={onTrashedChange}
            color="primary"
            sx={trashedValue ? { pointerEvents: 'none' } : undefined}
          />
        }
        label="Trashed"
        sx={trashedValue ? { pointerEvents: 'none' } : undefined}
      />
    </Box>

    <Box sx={{ display: 'flex', gap: 2 }}>
      <TextField
        fullWidth
        select={isEditMode}
        label="Freezing Session"
        disabled={!isEditMode}
        value={isEditMode ? editedData.freezingSessionId || '' : formData.freezingSession}
        onChange={(e) => onFieldChange('freezingSessionId', e.target.value ? parseInt(e.target.value) : null)}
        sx={!isEditMode ? disabledTextFieldStyles : { mb: 5 }}
      >
        <MenuItem value="">
          <em>None</em>
        </MenuItem>
        {freezingSessions?.map((session) => (
          <MenuItem key={session.id} value={session.id}>
            {session.display_name}
          </MenuItem>
        ))}
      </TextField>
      <TextField
        fullWidth
        select={isEditMode}
        label="Specimen"
        disabled={!isEditMode}
        value={isEditMode ? editedData.specimenId || '' : formData.specimen}
        onChange={(e) => onFieldChange('specimenId', e.target.value ? parseInt(e.target.value) : null)}
        sx={!isEditMode ? disabledTextFieldStyles : { mb: 5 }}
      >
        <MenuItem value="">
          <em>None</em>
        </MenuItem>
        {specimens?.map((specimen) => (
          <MenuItem key={specimen.id} value={specimen.id}>
            {specimen.display_name}
          </MenuItem>
        ))}
      </TextField>
    </Box>

    <Box sx={{ display: 'flex', gap: 2 }}>
      <TextField
        fullWidth
        select={isEditMode}
        label="Project"
        disabled={!isEditMode}
        value={isEditMode ? editedData.projectId || '' : formData.project}
        onChange={(e) => onFieldChange('projectId', e.target.value ? parseInt(e.target.value) : null)}
        sx={!isEditMode ? disabledTextFieldStyles : { mb: 5 }}
      >
        <MenuItem value="">
          <em>None</em>
        </MenuItem>
        {projects?.map((project) => (
          <MenuItem key={project.id} value={project.id}>
            {project.name}
          </MenuItem>
        ))}
      </TextField>
      <TextField
        fullWidth
        label="Position in Box"
        disabled={!isEditMode}
        value={isEditMode ? editedData.positionInBox : formData.positionInBox}
        onChange={(e) => onFieldChange('positionInBox', parseInt(e.target.value) || 1)}
        type="number"
        sx={!isEditMode ? disabledTextFieldStyles : { mb: 5 }}
      />
    </Box>

    <Box sx={{ display: 'flex', gap: 2 }}>
      <TextField
        fullWidth
        label="Blot Time"
        disabled={!isEditMode}
        value={isEditMode ? editedData.blotTime : formData.blotTime}
        onChange={(e) => onFieldChange('blotTime', parseFloat(e.target.value) || 0)}
        type="number"
        sx={!isEditMode ? disabledTextFieldStyles : { mb: 5 }}
      />
      <TextField
        fullWidth
        label="Blot Force"
        disabled={!isEditMode}
        value={isEditMode ? editedData.blotForce : formData.blotForce}
        onChange={(e) => onFieldChange('blotForce', parseFloat(e.target.value) || 0)}
        type="number"
        sx={!isEditMode ? disabledTextFieldStyles : { mb: 5 }}
      />
      <TextField
        fullWidth
        label="Blot Distance"
        disabled={!isEditMode}
        value={isEditMode ? editedData.blotDistance : formData.blotDistance}
        onChange={(e) => onFieldChange('blotDistance', parseFloat(e.target.value) || 0)}
        type="number"
        sx={!isEditMode ? disabledTextFieldStyles : { mb: 5 }}
      />
    </Box>

    <LabelsAutocomplete
      value={currentLabels}
      onChange={onLabelsChange}
      disabled={!isEditMode}
      sx={!isEditMode ? disabledTextFieldStyles : { mb: 5 }}
    />
  </>
);
