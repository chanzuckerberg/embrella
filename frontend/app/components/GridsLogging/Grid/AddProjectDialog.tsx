'use client';

import React, { useState } from 'react';
import { Box, TextField, Alert } from '@mui/material';
import { BaseFormDialog } from '@app/common/components/Forms/BaseFormDialog';
import { disabledTextFieldStyles } from '@app/components/GridsLogging/GridBox/DisableBoxStyle';
import { FormFieldWithAdd } from '@app/common/components/Forms/FormFieldWithAdd';
import { ProjectFormData } from '@app/common/types/gridLogging';
import { useCreateProject } from '@app/common/hooks/useGridLogging';

interface AddProjectDialogProps {
  open: boolean;
  onClose: () => void;
  onSave?: (projectId: number) => void;
  projectLeaders?: Array<{ id: number; username: string; full_name: string }>;
  confluenceSpaces?: Array<{ id: string; url: string }>;
  googleDriveFolders?: Array<{ id: string; name: string }>;
}

export const AddProjectDialog: React.FC<AddProjectDialogProps> = ({
  open,
  onClose,
  onSave,
  projectLeaders = [],
  confluenceSpaces = [],
  googleDriveFolders = [],
}) => {
  const { createProject, isCreating, error, clearError } = useCreateProject();
  const [formData, setFormData] = useState<ProjectFormData>({
    name: '',
    description: '',
    projectLeader: '',
    confluenceSpace: '',
    googleDriveFolder: '',
  });

  const handleInputChange = (field: keyof ProjectFormData, value: string) => {
    setFormData((prev) => ({
      ...prev,
      [field]: value,
    }));
  };

  const handleSave = async () => {
    if (!formData.name.trim()) {
      alert('Please enter a project name');
      return;
    }

    const result = await createProject({
      name: formData.name.trim(),
      description: formData.description.trim(),
      project_leader: formData.projectLeader ? Number(formData.projectLeader) : undefined,
      confluence_space: formData.confluenceSpace ? Number(formData.confluenceSpace) : undefined,
      google_drive_folder: formData.googleDriveFolder ? Number(formData.googleDriveFolder) : undefined,
    });

    if (result) {
      if (onSave) {
        onSave(result.project.id);
      }
      // Reset form
      setFormData({
        name: '',
        description: '',
        projectLeader: '',
        confluenceSpace: '',
        googleDriveFolder: '',
      });
      onClose();
    }
  };
  const handleClose = () => {
    // Reset form on close
    setFormData({
      name: '',
      description: '',
      projectLeader: '',
      confluenceSpace: '',
      googleDriveFolder: '',
    });
    onClose();
  };

  const isFormValid = formData.name.trim();

  return (
    <BaseFormDialog
      open={open}
      onClose={handleClose}
      title="Add New Project"
      onSave={handleSave}
      isSubmitting={isCreating}
      disabled={!isFormValid}
    >
      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
        {Boolean(error) && (
          <Alert severity="error" onClose={clearError}>
            {error}
          </Alert>
        )}
        <Box sx={{ display: 'flex', gap: 2 }}>
          <TextField
            required
            label="Project Name"
            placeholder="Enter project name (e.g., TRD06)"
            value={formData.name}
            onChange={(e) => handleInputChange('name', e.target.value)}
            sx={{ ...disabledTextFieldStyles, flex: 1 }}
          />

          <FormFieldWithAdd
            label="Project Leader"
            value={formData.projectLeader}
            onChange={(value) => handleInputChange('projectLeader', value)}
            options={projectLeaders.map((leader) => ({
              value: leader.id.toString(),
              label: leader.full_name || leader.username,
            }))}
          />
        </Box>

        <TextField
          label="Description"
          placeholder="Enter project description (optional)"
          value={formData.description}
          onChange={(e) => handleInputChange('description', e.target.value)}
          multiline
          rows={3}
          sx={disabledTextFieldStyles}
        />

        <Box sx={{ display: 'flex', gap: 2 }}>
          <FormFieldWithAdd
            label="Confluence Space"
            value={formData.confluenceSpace}
            onChange={(value) => handleInputChange('confluenceSpace', value)}
            options={confluenceSpaces.map((space) => ({ value: space.id, label: space.url }))}
          />
          <FormFieldWithAdd
            label="Google Drive Folder"
            value={formData.googleDriveFolder}
            onChange={(value) => handleInputChange('googleDriveFolder', value)}
            options={googleDriveFolders.map((folder) => ({ value: folder.id, label: folder.name }))}
          />
        </Box>
      </Box>
    </BaseFormDialog>
  );
};
