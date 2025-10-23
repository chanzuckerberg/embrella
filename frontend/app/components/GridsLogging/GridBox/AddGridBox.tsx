'use client';

import React, { useState } from 'react';
import { Box, TextField, MenuItem, FormControl, InputLabel, Select } from '@mui/material';
import { UsersList } from '@app/common/types/gridLogging/userList';
import { useGridLoggingChoices } from '@app/common/hooks/useGridLogging/useGridLoggingChoices';
import { useGridLoggingUserList } from '@app/common/hooks/useGridLogging/useGridLoggingUserList';
import { disabledTextFieldStyles } from '../GridBox/DisableBoxStyle';
import { BaseFormDialog } from '@app/common/components/Forms/BaseFormDialog';

interface AddGridBoxProps {
  open: boolean;
  onClose: () => void;
  selectedUser?: UsersList | null;
  puckId?: number;
  puckName?: string;
  positionInPuck?: number;
}

export const AddGridBox: React.FC<AddGridBoxProps> = ({
  open,
  onClose,
  selectedUser,
  puckId,
  puckName,
  positionInPuck,
}) => {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [formData, setFormData] = useState({
    user: selectedUser?.id || '',
    gridBoxName: '',
    color: '',
    numbering: '',
    puck: puckId || '',
    puckName: puckName || '',
    positionInPuck: positionInPuck || '',
    maxGrids: '',
  });

  const { choices, isSuccess: choicesLoaded } = useGridLoggingChoices();
  const { isSuccess: usersLoaded } = useGridLoggingUserList();

  const handleInputChange = (field: string, value: string | number) => {
    setFormData((prev) => ({
      ...prev,
      [field]: value,
    }));
  };

  const handleSave = () => {
    // Validate required fields
    if (
      !formData.user ||
      !formData.gridBoxName ||
      !formData.color ||
      !formData.numbering ||
      !formData.puck ||
      !formData.positionInPuck ||
      !formData.maxGrids
    ) {
      alert('Please fill in all required fields');
      return;
    }

    setIsSubmitting(true);
    console.log('Saving grid box:', formData);
    // TODO: Add API call to save grid box
  };

  const isFormValid =
    formData.user &&
    formData.gridBoxName &&
    formData.color &&
    formData.numbering &&
    formData.puck &&
    formData.positionInPuck &&
    formData.maxGrids;

  return (
    <BaseFormDialog
      open={open}
      onClose={onClose}
      title="Add a Grid Box"
      subtitle={selectedUser?.full_name || ''}
      onSave={handleSave}
      isSubmitting={isSubmitting}
      disabled={!isFormValid || !choicesLoaded || !usersLoaded}
    >
      <Box sx={{ display: 'flex', gap: 2 }}>
        <TextField
          required
          label="Grid Box Name"
          placeholder="Grid Box Name [Ex. Puck5Slot4Pos2]"
          value={formData.gridBoxName}
          onChange={(e) => handleInputChange('gridBoxName', e.target.value)}
          sx={{ ...disabledTextFieldStyles, flex: 1 }}
        />
        <TextField
          required
          label="Puck Name"
          value={formData.puckName}
          onChange={(e) => handleInputChange('puckName', e.target.value)}
          disabled
          sx={{ ...disabledTextFieldStyles, flex: 1 }}
        />
      </Box>

      <Box sx={{ display: 'flex', gap: 2 }}>
        {positionInPuck !== undefined ? (
          <TextField
            required
            label="Position in Puck"
            value={positionInPuck}
            disabled
            sx={{ ...disabledTextFieldStyles, flex: 1 }}
          />
        ) : (
          <FormControl required sx={{ flex: 1 }}>
            <InputLabel id="position-label">Position in Puck</InputLabel>
            <Select
              labelId="position-label"
              value={formData.positionInPuck}
              onChange={(e) => handleInputChange('positionInPuck', e.target.value)}
              label="Position in Puck"
              sx={disabledTextFieldStyles}
            >
              {Array.from({ length: 12 }, (_, i) => i + 1).map((position) => (
                <MenuItem key={position} value={position}>
                  Position {position}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
        )}

        <FormControl required sx={{ flex: 1 }}>
          <InputLabel id="numbering-label">Numbering</InputLabel>
          <Select
            labelId="numbering-label"
            value={formData.numbering}
            onChange={(e) => handleInputChange('numbering', e.target.value)}
            label="Numbering"
            disabled={!choicesLoaded}
            sx={disabledTextFieldStyles}
          >
            {choices?.grid_box_numbering?.map((numbering) => (
              <MenuItem key={numbering.value} value={numbering.value}>
                {numbering.label}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
      </Box>

      <Box sx={{ display: 'flex', gap: 2 }}>
        <FormControl required sx={{ flex: 1 }}>
          <InputLabel id="color-label">Color</InputLabel>
          <Select
            labelId="color-label"
            value={formData.color}
            onChange={(e) => handleInputChange('color', e.target.value)}
            label="Color"
            disabled={!choicesLoaded}
            sx={disabledTextFieldStyles}
          >
            {choices?.grid_box_colors?.map((color) => (
              <MenuItem key={color.value} value={color.value}>
                {color.label}
              </MenuItem>
            ))}
          </Select>
        </FormControl>

        <FormControl required sx={{ flex: 1 }}>
          <InputLabel id="max-grids-label">Max Grids</InputLabel>
          <Select
            labelId="max-grids-label"
            value={formData.maxGrids}
            onChange={(e) => handleInputChange('maxGrids', e.target.value)}
            label="Max Number of Grids"
            sx={disabledTextFieldStyles}
          >
            <MenuItem value={4}>4</MenuItem>
            <MenuItem value={6}>6</MenuItem>
            <MenuItem value={8}>8</MenuItem>
          </Select>
        </FormControl>
      </Box>
    </BaseFormDialog>
  );
};
