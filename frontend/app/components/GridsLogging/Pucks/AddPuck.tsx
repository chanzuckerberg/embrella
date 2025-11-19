'use client';

import React, { useState, useEffect } from 'react';
import { Box, TextField, MenuItem, FormControl, InputLabel, Select, InputAdornment, Alert } from '@mui/material';
import { useGridLoggingChoices, useGridLoggingUserList, useGridLoggingCaneList, useGridLoggingPucksByCane, useCreatePuck } from '@app/common/hooks/useGridLogging';
import { disabledTextFieldStyles } from '../GridBox/DisableBoxStyle';
import { BaseFormDialog } from '@app/common/components/Forms/BaseFormDialog';
import { PuckList, UserList } from '@app/common/types/gridLogging';

interface AddPuckProps {
  open: boolean;
  onClose: () => void;
  selectedUser?: UserList | null;
  caneId?: number;
  onPuckCreated: (puck: PuckList) => void;
}

export const AddPuck: React.FC<AddPuckProps> = ({ open, onClose, selectedUser, caneId, onPuckCreated }) => {
  const [formData, setFormData] = useState({
    user: selectedUser?.id || 0,
    puckName: '',
    color: 'CF1E01',
    cane: caneId || '',
    positionInCane: '',
  });

  const { choices, isSuccess: choicesLoaded } = useGridLoggingChoices();
  const { isSuccess: usersLoaded } = useGridLoggingUserList();
  const { canes, isSuccess: canesLoaded } = useGridLoggingCaneList();
  const { createPuck, isCreating, error, clearError } = useCreatePuck();
  
  // fetch pucks for the selected cane 
  const { pucks: pucksData } = useGridLoggingPucksByCane(
    formData.cane ? Number(formData.cane) : undefined
  );

  // Reset form when dialog opens
  useEffect(() => {
    if (open) {
      setFormData({
        user: selectedUser?.id || 0,
        puckName: '',
        color: 'CF1E01',
        cane: caneId || '',
        positionInCane: '',
      });
      clearError();
    }
  }, [open, selectedUser?.id, caneId, clearError]);

  useEffect(() => {
    if (selectedUser?.id) {
      setFormData((prev) => ({
        ...prev,
        user: selectedUser.id,
      }));
    }
  }, [selectedUser?.id]);

  // Reset position when cane changes
  useEffect(() => {
    if (formData.cane) {
      setFormData((prev) => ({
        ...prev,
        positionInCane: '',
      }));
    }
  }, [formData.cane]);

  const handleInputChange = (field: string, value: string | number) => {
    setFormData((prev) => ({
      ...prev,
      [field]: value,
    }));
  };

  const handleSave = async () => {
    // Validate required fields
    if (!formData.puckName || !formData.cane || !formData.positionInCane) {
      alert('Please fill in all required fields');
      return;
    }

    const newPuck = await createPuck({
      user_id: Number(formData.user),
      puckName: formData.puckName,
      color: formData.color,
      cane: Number(formData.cane),
      position_in_cane: Number(formData.positionInCane),
    });

    if (newPuck) {
      onClose();
      if (onPuckCreated) {
        onPuckCreated(newPuck);
      }
    }
  };

  const isFormValid = formData.puckName && formData.cane && formData.positionInCane;

  return (
    <BaseFormDialog
      open={open}
      onClose={onClose}
      title="Add Puck"
      subtitle={selectedUser?.full_name || ''}
      onSave={handleSave}
      isSubmitting={isCreating}
      disabled={!isFormValid || !choicesLoaded || !usersLoaded || !canesLoaded}
    >
      {Boolean(error) && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}
      
      <Box sx={{ display: 'flex', gap: 2 }}>
        <TextField
          required
          label="Puck Name"
          placeholder="Ex. Puck 4"
          value={formData.puckName}
          onChange={(e) => handleInputChange('puckName', e.target.value)}
          InputProps={{
            startAdornment: (
              <InputAdornment position="start" sx={{ color: 'rgba(0, 0, 0, 0.87)', mr: -4 }}>
                CZII-0
              </InputAdornment>
            ),
          }}
          sx={{
            ...disabledTextFieldStyles,
            flex: 1,
            '& .MuiInputBase-input': { paddingLeft: 0 },
          }}
        />
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
            {choices?.puck_colors?.map((color) => (
              <MenuItem key={color.value} value={color.value}>
                {color.label}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
      </Box>

      <Box sx={{ display: 'flex', gap: 2 }}>
        <FormControl required sx={{ flex: 1 }}>
          <InputLabel id="cane-label">Cane</InputLabel>
          <Select
            labelId="cane-label"
            value={formData.cane}
            onChange={(e) => handleInputChange('cane', e.target.value)}
            label="Cane"
            sx={disabledTextFieldStyles}
          >
            {!canesLoaded && <MenuItem value="">Loading canes...</MenuItem>}
            {canesLoaded && canes.length === 0 && (
              <MenuItem value="">No canes available</MenuItem>
            )}
            {canes.map((cane) => (
              <MenuItem key={cane.id} value={cane.id}>
                {cane.color_code} 
              </MenuItem>
            ))}
          </Select>
        </FormControl>

        <FormControl required sx={{ flex: 1 }}>
          <InputLabel id="position-label">Position in Cane</InputLabel>
          <Select
            labelId="position-label"
            value={formData.positionInCane}
            onChange={(e) => handleInputChange('positionInCane', e.target.value)}
            label="Position in Cane"
            disabled={!formData.cane}
            sx={disabledTextFieldStyles}
            MenuProps={{
              PaperProps: {
                style: {
                  maxHeight: 180,
                },
              },
            }}
          >
            {!formData.cane && <MenuItem value="">Select a cane first</MenuItem>}
            {/* Positions with status indicators - */}
            {Array.from({ length: 10 }, (_, i) => i + 1).map((position) => {
              // Check if this position is filled by finding a puck at this position
              const puckAtPosition = pucksData?.pucks?.find(
                (puck) => puck.position_in_cane === position
              );
              const isFilled = !!puckAtPosition;

              return (
                <MenuItem key={position} value={position} disabled={isFilled}>
                  Position {position} {isFilled ? '(Filled)' : '(Available)'}
                </MenuItem>
              );
            })}
          </Select>
        </FormControl>
      </Box>
    </BaseFormDialog>
  );
};