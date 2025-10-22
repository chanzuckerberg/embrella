'use client';

import React, { useState } from 'react';
import { Box, CircularProgress, TextField, MenuItem, FormControl, InputLabel, Select, IconButton } from '@mui/material';
import { Button, Dialog, DialogTitle, DialogContent, Icon } from '@czi-sds/components';
import { UsersList } from '@app/common/types/gridLogging/userList';
import { useGridLoggingChoices } from '@app/common/hooks/useGridLogging/useGridLoggingChoices';
import { useGridLoggingUserList } from '@app/common/hooks/useGridLogging/useGridLoggingUserList';
import { disabledTextFieldStyles } from '../GridBox/DisableBoxStyle';

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
  const [newSpecimenName, setNewSpecimenName] = useState('');
  const [newProjectName, setNewProjectName] = useState('');
  const [newFreezingSessionName, setNewFreezingSessionName] = useState('');
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

  const handleAddSpecimen = () => {
    if (newSpecimenName.trim()) {
      console.log('Adding new specimen:', newSpecimenName);
      setNewSpecimenName('');
      setAddSpecimenDialogOpen(false);
    }
  };

  const handleAddProject = () => {
    if (newProjectName.trim()) {
      console.log('Adding new project:', newProjectName);
      setNewProjectName('');
      setAddProjectDialogOpen(false);
    }
  };

  const handleAddFreezingSession = () => {
    if (newFreezingSessionName.trim()) {
      console.log('Adding new freezing session:', newFreezingSessionName);
      setNewFreezingSessionName('');
      setAddFreezingSessionDialogOpen(false);
    }
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
      <Dialog onClose={onClose} open={open} sdsSize="xs">
        <DialogTitle title="Create a Grid" subtitle={selectedUser?.full_name || ''} onClose={onClose} />
        <DialogContent>
          <Box
            sx={{
              display: 'flex',
              flexDirection: 'column',
              gap: 3,
              pt: 2,
              pb: 2,
              mt: 2,
            }}
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
              <FormControl sx={{ flex: 1 }}>
                <InputLabel id="freezing-session-label">Freezing Session</InputLabel>
                <Select
                  labelId="freezing-session-label"
                  value={formData.freezingSession}
                  onChange={(e) => handleInputChange('freezingSession', e.target.value)}
                  label="Freezing Session"
                  disabled={!choicesLoaded}
                  sx={disabledTextFieldStyles}
                >
                  <MenuItem value="">Select Freezing Session</MenuItem>
                </Select>
              </FormControl>
              <IconButton
                onClick={() => setAddFreezingSessionDialogOpen(true)}
                sx={{
                  mt: 5,
                  color: 'primary.main',
                  '&:hover': {
                    backgroundColor: 'primary.light',
                    color: 'white',
                  },
                }}
                size="small"
              >
                <Icon sdsIcon="Plus" sdsSize="s" />
              </IconButton>
            </Box>

            <Box sx={{ display: 'flex', gap: 2, alignItems: 'flex-start' }}>
              <FormControl required sx={{ flex: 1 }}>
                <InputLabel id="specimen-label">Specimen</InputLabel>
                <Select
                  labelId="specimen-label"
                  value={formData.specimen}
                  onChange={(e) => handleInputChange('specimen', e.target.value)}
                  label="Specimen"
                  disabled={!choicesLoaded}
                  sx={disabledTextFieldStyles}
                >
                  <MenuItem value="">Select Specimen</MenuItem>
                </Select>
              </FormControl>
              <IconButton
                onClick={() => setAddSpecimenDialogOpen(true)}
                sx={{
                  mt: 5,
                  color: 'primary.main',
                  '&:hover': {
                    backgroundColor: 'primary.light',
                    color: 'white',
                  },
                }}
                size="small"
              >
                <Icon sdsIcon="Plus" sdsSize="s" />
              </IconButton>
              <FormControl required sx={{ flex: 1 }}>
                <InputLabel id="project-label">Project</InputLabel>
                <Select
                  labelId="project-label"
                  value={formData.project}
                  onChange={(e) => handleInputChange('project', e.target.value)}
                  label="Project"
                  disabled={!choicesLoaded}
                  sx={disabledTextFieldStyles}
                >
                  <MenuItem value="">Select Project</MenuItem>
                </Select>
              </FormControl>
              <IconButton
                onClick={() => setAddProjectDialogOpen(true)}
                sx={{
                  mt: 5,
                  color: 'primary.main',
                  '&:hover': {
                    backgroundColor: 'primary.light',
                    color: 'white',
                  },
                }}
                size="small"
              >
                <Icon sdsIcon="Plus" sdsSize="s" />
              </IconButton>
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

            <Box
              sx={{
                display: 'flex',
                justifyContent: 'flex-end',
                gap: 2,
              }}
            >
              <Button sdsType="secondary" sdsStyle="rounded" onClick={onClose} disabled={isSubmitting}>
                Cancel
              </Button>
              <Button
                sdsType="primary"
                sdsStyle="rounded"
                onClick={handleSave}
                disabled={isSubmitting || !choicesLoaded || !usersLoaded}
                startIcon={isSubmitting ? <CircularProgress size={16} /> : undefined}
              >
                {isSubmitting ? 'Saving...' : 'Save'}
              </Button>
            </Box>
          </Box>
        </DialogContent>
      </Dialog>

      {/* Add Specimen Dialog */}
      <Dialog onClose={() => setAddSpecimenDialogOpen(false)} open={addSpecimenDialogOpen} sdsSize="xs">
        <DialogTitle title="Add New Specimen" onClose={() => setAddSpecimenDialogOpen(false)} />
        <DialogContent>
          <Box
            sx={{
              display: 'flex',
              flexDirection: 'column',
              gap: 3,
              pt: 2,
              pb: 2,
              mt: 2,
            }}
          >
            <TextField
              required
              label="Specimen Name"
              placeholder="Enter specimen name"
              value={newSpecimenName}
              onChange={(e) => setNewSpecimenName(e.target.value)}
              sx={disabledTextFieldStyles}
            />
            
            <Box
              sx={{
                display: 'flex',
                justifyContent: 'flex-end',
                gap: 2,
              }}
            >
              <Button 
                sdsType="secondary" 
                sdsStyle="rounded" 
                onClick={() => setAddSpecimenDialogOpen(false)}
              >
                Cancel
              </Button>
              <Button
                sdsType="primary"
                sdsStyle="rounded"
                onClick={handleAddSpecimen}
                disabled={!newSpecimenName.trim()}
              >
                Add Specimen
              </Button>
            </Box>
          </Box>
        </DialogContent>
      </Dialog>

      {/* Add Project Dialog */}
      <Dialog onClose={() => setAddProjectDialogOpen(false)} open={addProjectDialogOpen} sdsSize="xs">
        <DialogTitle title="Add New Project" onClose={() => setAddProjectDialogOpen(false)} />
        <DialogContent>
          <Box
            sx={{
              display: 'flex',
              flexDirection: 'column',
              gap: 3,
              pt: 2,
              pb: 2,
              mt: 2,
            }}
          >
            <TextField
              required
              label="Project Name"
              placeholder="Enter project name"
              value={newProjectName}
              onChange={(e) => setNewProjectName(e.target.value)}
              sx={disabledTextFieldStyles}
            />
            
            <Box
              sx={{
                display: 'flex',
                justifyContent: 'flex-end',
                gap: 2,
              }}
            >
              <Button 
                sdsType="secondary" 
                sdsStyle="rounded" 
                onClick={() => setAddProjectDialogOpen(false)}
              >
                Cancel
              </Button>
              <Button
                sdsType="primary"
                sdsStyle="rounded"
                onClick={handleAddProject}
                disabled={!newProjectName.trim()}
              >
                Add Project
              </Button>
            </Box>
          </Box>
        </DialogContent>
      </Dialog>

      {/* Add Freezing Session Dialog */}
      <Dialog onClose={() => setAddFreezingSessionDialogOpen(false)} open={addFreezingSessionDialogOpen} sdsSize="xs">
        <DialogTitle title="Add New Freezing Session" onClose={() => setAddFreezingSessionDialogOpen(false)} />
        <DialogContent>
          <Box
            sx={{
              display: 'flex',
              flexDirection: 'column',
              gap: 3,
              pt: 2,
              pb: 2,
              mt: 2,
            }}
          >
            <TextField
              required
              label="Freezing Session Name"
              placeholder="Enter freezing session name"
              value={newFreezingSessionName}
              onChange={(e) => setNewFreezingSessionName(e.target.value)}
              sx={disabledTextFieldStyles}
            />
            
            <Box
              sx={{
                display: 'flex',
                justifyContent: 'flex-end',
                gap: 2,
              }}
            >
              <Button 
                sdsType="secondary" 
                sdsStyle="rounded" 
                onClick={() => setAddFreezingSessionDialogOpen(false)}
              >
                Cancel
              </Button>
              <Button
                sdsType="primary"
                sdsStyle="rounded"
                onClick={handleAddFreezingSession}
                disabled={!newFreezingSessionName.trim()}
              >
                Add Freezing Session
              </Button>
            </Box>
          </Box>
        </DialogContent>
      </Dialog>
    </>
  );
};