'use client';

import React, { useState } from 'react';
import { Box, TextField, FormControl, InputLabel, Select, MenuItem, Alert } from '@mui/material';
import { BaseFormDialog } from '@app/common/components/Forms/BaseFormDialog';
import { disabledTextFieldStyles } from '@app/components/GridsLogging/GridBox/DisableBoxStyle';
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
  const [isSubmitting, setIsSubmitting] = useState(false);
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
      isSubmitting={isSubmitting}
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

          <FormControl sx={{ flex: 1 }}>
            <InputLabel id="project-leader-label">Project Leader</InputLabel>
            <Select
              labelId="project-leader-label"
              value={formData.projectLeader}
              onChange={(e) => handleInputChange('projectLeader', e.target.value)}
              label="Project Leader"
              sx={disabledTextFieldStyles}
              MenuProps={{
                PaperProps: {
                  style: {
                    maxHeight: 180,
                  },
                },
              }}
            >
              <MenuItem value="">
                <em>None</em>
              </MenuItem>
              {projectLeaders.length === 0 ? (
                <MenuItem value="" disabled>
                  No project leaders available
                </MenuItem>
              ) : (
                projectLeaders.map((leader) => (
                  <MenuItem key={leader.id} value={leader.id.toString()}>
                    {leader.full_name || leader.username}
                  </MenuItem>
                ))
              )}
            </Select>
          </FormControl>
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
          <FormControl sx={{ flex: 1 }}>
            <InputLabel id="confluence-space-label">Confluence Space</InputLabel>
            <Select
              labelId="confluence-space-label"
              value={formData.confluenceSpace}
              onChange={(e) => handleInputChange('confluenceSpace', e.target.value)}
              label="Confluence Space"
              sx={disabledTextFieldStyles}
            >
              <MenuItem value="">
                <em>None</em>
              </MenuItem>
              {confluenceSpaces.length === 0 ? (
                <MenuItem value="" disabled>
                  No confluence spaces available
                </MenuItem>
              ) : (
                confluenceSpaces.map((space) => (
                  <MenuItem key={space.id} value={space.id}>
                    {space.url}
                  </MenuItem>
                ))
              )}
            </Select>
          </FormControl>

          <FormControl sx={{ flex: 1 }}>
            <InputLabel id="google-drive-folder-label">Google Drive Folder</InputLabel>
            <Select
              labelId="google-drive-folder-label"
              value={formData.googleDriveFolder}
              onChange={(e) => handleInputChange('googleDriveFolder', e.target.value)}
              label="Google Drive Folder"
              sx={disabledTextFieldStyles}
            >
              <MenuItem value="">
                <em>None</em>
              </MenuItem>
              {googleDriveFolders.length === 0 ? (
                <MenuItem value="" disabled>
                  No google drive folders available
                </MenuItem>
              ) : (
                googleDriveFolders.map((folder) => (
                  <MenuItem key={folder.id} value={folder.id}>
                    {folder.name}
                  </MenuItem>
                ))
              )}
            </Select>
          </FormControl>
        </Box>
      </Box>
    </BaseFormDialog>
  );
};
