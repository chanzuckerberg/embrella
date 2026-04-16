'use client';

import React, { useState, useEffect } from 'react';
import { Box, TextField, MenuItem, FormControl, InputLabel, Select, InputAdornment, Alert } from '@mui/material';
import { UserList } from '@app/common/types/gridLogging';
import {
  useCreateGridBox,
  useGridLoggingChoices,
  useGridLoggingPuckSlots,
  useGridLoggingUserList,
} from '@app/common/hooks/useGridLogging';
import { disabledTextFieldStyles } from '../GridBox/DisableBoxStyle';
import { BaseFormDialog } from '@app/common/components/Forms/BaseFormDialog';

interface AddGridBoxProps {
  open: boolean;
  onClose: () => void;
  selectedUser?: UserList | null;
  puckId?: number;
  puckName?: string;
  positionInPuck?: number;
  onGridBoxCreated?: (slotPosition: number) => void;
}

export const AddGridBox: React.FC<AddGridBoxProps> = ({
  open,
  onClose,
  selectedUser,
  puckId,
  puckName,
  positionInPuck,
  onGridBoxCreated,
}) => {
  // const [isSubmitting, setIsSubmitting] = useState(false);
  const [formData, setFormData] = useState({
    user: selectedUser?.id || '',
    gridBoxName: '',
    color: 'FFFFFF',
    numbering: 'ucw',
    puck: puckId || '',
    puckName: puckName || '',
    positionInPuck: positionInPuck || '',
    maxGrids: '4',
  });

  const { choices, isSuccess: choicesLoaded } = useGridLoggingChoices();
  const { isSuccess: usersLoaded } = useGridLoggingUserList();
  const { createGridBox, isCreating, error, clearError } = useCreateGridBox();

  // fetch slots data when puckId is available
  const { slotsData, refetch: refetchPuckSlots } = useGridLoggingPuckSlots(puckId);
  // Reset form when dialog opens
  useEffect(() => {
    if (open) {
      setFormData({
        user: selectedUser?.id || '',
        gridBoxName: '',
        color: 'FFFFFF',
        numbering: 'ucw',
        puck: puckId || '',
        puckName: puckName || '',
        positionInPuck: positionInPuck || '',
        maxGrids: '4',
      });
      clearError();
    }
  }, [open, selectedUser?.id, puckId, puckName, positionInPuck, clearError]);

  useEffect(() => {
    if (open && puckId) {
      refetchPuckSlots();
    }
  }, [open, puckId, refetchPuckSlots]);

  const handleInputChange = (field: string, value: string | number) => {
    setFormData((prev) => ({
      ...prev,
      [field]: value,
    }));
  };

  const handleSave = async () => {
    // Validate required fields
    if (
      !formData.user ||
      !formData.gridBoxName ||
      !formData.numbering ||
      !formData.puck ||
      !formData.positionInPuck ||
      !formData.maxGrids
    ) {
      alert('Please fill in all required fields');
      return;
    }

    const result = await createGridBox({
      puck_id: Number(formData.puck),
      puckName: formData.puckName,
      gridBoxName: formData.gridBoxName,
      color: formData.color,
      numbering: formData.numbering,
      position_in_puck: Number(formData.positionInPuck),
      max_grids: Number(formData.maxGrids),
    });

    if (result) {
      onClose();
      // Navigate to the newly created gridbox
      if (onGridBoxCreated) {
        onGridBoxCreated(Number(formData.positionInPuck));
      }
    }
  };

  const isFormValid =
    formData.gridBoxName &&
    formData.numbering &&
    formData.puck &&
    (positionInPuck || formData.positionInPuck) &&
    formData.maxGrids;

  return (
    <BaseFormDialog
      open={open}
      onClose={onClose}
      title="Add a Grid Box"
      subtitle={selectedUser?.full_name || ''}
      onSave={handleSave}
      isSubmitting={isCreating}
      disabled={!isFormValid || !choicesLoaded || !usersLoaded}
    >
      {Boolean(error) && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      <TextField
        required
        label="Grid Box Name"
        placeholder="Grid Box Name [Ex. Puck5Slot4Pos2]"
        value={formData.gridBoxName}
        onChange={(e) => handleInputChange('gridBoxName', e.target.value)}
        InputProps={{
          startAdornment: (
            <InputAdornment position="start" sx={{ color: 'rgba(0, 0, 0, 0.87)', mr: -4 }}>
              Box-
            </InputAdornment>
          ),
        }}
        sx={{
          ...disabledTextFieldStyles,
          flex: 1,
          '& .MuiInputBase-input': { paddingLeft: 0 },
        }}
      />
      <TextField
        required
        label="Puck Name"
        value={formData.puckName}
        onChange={(e) => handleInputChange('puckName', e.target.value)}
        disabled
        sx={{ ...disabledTextFieldStyles, flex: 1 }}
      />

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
              {Array.from({ length: 12 }, (_, i) => i + 1).map((position) => {
                const slotData = slotsData?.slots.find((slot) => slot.position === position);
                const status = slotData?.status || 'unknown';
                const isFilled = status === 'filled';

                return (
                  <MenuItem key={position} value={position} disabled={isFilled}>
                    Position {position} {isFilled ? '(Filled)' : '(Available)'}
                  </MenuItem>
                );
              })}
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
        <FormControl sx={{ flex: 1 }}>
          <InputLabel id="color-label">Color</InputLabel>
          <Select
            labelId="color-label"
            value={formData.color}
            onChange={(e) => handleInputChange('color', e.target.value)}
            label="Color"
            disabled={!choicesLoaded}
            sx={disabledTextFieldStyles}
            MenuProps={{
              PaperProps: {
                style: {
                  maxHeight: 180,
                },
              },
            }}
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
            label="Max Grids"
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
