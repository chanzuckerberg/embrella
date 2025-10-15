'use client';

import React, { useState } from 'react';
import { Box, CircularProgress, TextField, MenuItem, FormControl, InputLabel, Select, Checkbox, FormControlLabel } from '@mui/material';
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

  const handleSave = () => {
    // Validate required fields
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
          <Box sx={{ display: 'flex', gap: 2 }}>
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
          </Box>

          <Box sx={{ display: 'flex', gap: 2 }}>
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
              label="Blot Force"
              value={formData.blotDistance}
              onChange={(e) => handleInputChange('blotDistance', e.target.value)}
              sx={{ ...disabledTextFieldStyles, flex: 1 }}
            />
          </Box>

          {/* <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
            <Button
              sdsType="secondary"
              sdsStyle="rounded"
              startIcon={<Icon sdsIcon="Copy" sdsSize="s" />}
              disabled={isSubmitting}
            >
              Duplicate
            </Button>
            <FormControlLabel
              control={
                <Checkbox
                  checked={formData.clipped}
                  onChange={(e) => handleInputChange('clipped', e.target.checked)}
                  sx={{ color: 'primary.main' }}
                />
              }
              label="Clipped"
            />
          </Box> */}

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
  );
};