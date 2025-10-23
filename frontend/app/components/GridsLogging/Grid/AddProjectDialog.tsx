'use client';

import React, { useState } from 'react';
import { Box, TextField, FormControl, InputLabel, Select, MenuItem } from '@mui/material';
import { BaseFormDialog } from '@app/common/components/Forms/BaseFormDialog';
import { disabledTextFieldStyles } from '@app/components/GridsLogging/GridBox/DisableBoxStyle';

interface ProjectFormData {
  name: string;
  description: string;
  projectLeader: string;
  confluenceSpace: string;
  googleDriveFolder: string;
}

interface AddProjectDialogProps {
  open: boolean;
  onClose: () => void;
  onSave: (data: ProjectFormData) => void;
  projectLeaders?: Array<{ id: string; name: string }>;
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
    // Validate required fields
    if (!formData.name.trim() || !formData.projectLeader || !formData.confluenceSpace || !formData.googleDriveFolder) {
      alert('Please fill in all required fields');
      return;
    }

    setIsSubmitting(true);
    try {
      await onSave({
        name: formData.name.trim(),
        description: formData.description.trim(),
        projectLeader: formData.projectLeader,
        confluenceSpace: formData.confluenceSpace,
        googleDriveFolder: formData.googleDriveFolder,
      });
      // Reset form
      setFormData({
        name: '',
        description: '',
        projectLeader: '',
        confluenceSpace: '',
        googleDriveFolder: '',
      });
      onClose();
    } catch (error) {
      console.error('Error saving project:', error);
      alert('Failed to save project. Please try again.');
    } finally {
      setIsSubmitting(false);
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

  const isFormValid =
    formData.name.trim() &&
    formData.projectLeader &&
    formData.confluenceSpace &&
    formData.googleDriveFolder;

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
        <Box sx={{ display: 'flex', gap: 2 }}>
          <TextField
            required
            label="Project Name"
            placeholder="Enter project name"
            value={formData.name}
            onChange={(e) => handleInputChange('name', e.target.value)}
            sx={{ ...disabledTextFieldStyles, flex: 1 }}
          />

          <FormControl required sx={{ flex: 1 }}>
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
              {projectLeaders.length === 0 ? (
                <MenuItem value="" disabled>
                  No project leaders available
                </MenuItem>
              ) : (
                projectLeaders.map((leader) => (
                  <MenuItem key={leader.id} value={leader.id}>
                    {leader.name}
                  </MenuItem>
                ))
              )}
            </Select>
          </FormControl>
        </Box>

        <TextField
          label="Description"
          placeholder="Enter project description"
          value={formData.description}
          onChange={(e) => handleInputChange('description', e.target.value)}
          multiline
          rows={3}
          sx={disabledTextFieldStyles}
        />

        <Box sx={{ display: 'flex', gap: 2 }}>
          <FormControl required sx={{ flex: 1 }}>
            <InputLabel id="confluence-space-label">Confluence Space</InputLabel>
            <Select
              labelId="confluence-space-label"
              value={formData.confluenceSpace}
              onChange={(e) => handleInputChange('confluenceSpace', e.target.value)}
              label="Confluence Space"
              sx={disabledTextFieldStyles}
            >
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

          <FormControl required sx={{ flex: 1 }}>
            <InputLabel id="google-drive-folder-label">Google Drive Folder</InputLabel>
            <Select
              labelId="google-drive-folder-label"
              value={formData.googleDriveFolder}
              onChange={(e) => handleInputChange('googleDriveFolder', e.target.value)}
              label="Google Drive Folder"
              sx={disabledTextFieldStyles}
            >
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