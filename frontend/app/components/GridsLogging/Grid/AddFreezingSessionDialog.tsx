'use client';

import React, { useState } from 'react';
import { Box, TextField, FormControl, InputLabel, Select, MenuItem } from '@mui/material';
import { BaseFormDialog } from '@app/common/components/Forms/BaseFormDialog';
import { disabledTextFieldStyles } from '@app/components/GridsLogging/GridBox/DisableBoxStyle';
import { Device, ConfluencePage, UserList, FreezingSessionFormData } from '@app/common/types/gridLogging';
import { DateTimePicker } from '@mui/x-date-pickers/DateTimePicker'; 
import { LocalizationProvider } from '@mui/x-date-pickers/LocalizationProvider';
import { AdapterDateFns } from '@mui/x-date-pickers/AdapterDateFns';

export const AddFreezingSessionDialog: React.FC<{
  open: boolean;
  onClose: () => void;
  onSave: (data: FreezingSessionFormData) => void;
  users?: UserList[];
  devices?: Device[];
  notesPages?: ConfluencePage[];
  freezingSessionDate?: Date | null;
}> = ({ open, onClose, onSave, users = [], devices = [], notesPages = [], freezingSessionDate = null }) => {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [formData, setFormData] = useState<FreezingSessionFormData>({
    user: '',
    device: 'Leica GP2',
    temperature: '',
    humidity: '',
    notesPage: '',
    freezingSessionDate: null,
  });

  const handleInputChange = (field: keyof FreezingSessionFormData, value: string) => {
    setFormData((prev) => ({
      ...prev,
      [field]: value,
    }));
  };

  const handleSave = async () => {
    // Validate required fields
    if (!formData.user || !formData.device ) {
      alert('Please fill in all required fields (User andDevice)');
      return;
    }

    // Validate numbers
    if (isNaN(Number(formData.temperature)) || isNaN(Number(formData.humidity))) {
      alert('Temperature and Humidity must be valid numbers');
      return;
    }

    setIsSubmitting(true);
    try {
      await onSave({
        user: formData.user,
        device: formData.device,
        temperature: formData.temperature,
        humidity: formData.humidity,
        notesPage: formData.notesPage,
        freezingSessionDate: formData.freezingSessionDate,
      });
      // Reset form
      setFormData({
        user: '',
        device: '',
        temperature: '',
        humidity: '',
        notesPage: '',
        freezingSessionDate: null,
      });
      onClose();
    } catch (error) {
      console.error('Error saving freezing session:', error);
      alert('Failed to save freezing session. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleClose = () => {
    // Reset form on close
    setFormData({
      user: '',
      device: '',
      temperature: '',
      humidity: '',
      notesPage: '',
      freezingSessionDate: null,
    });
    onClose();
  };
  const handleDateChange = (date: Date | null) => {
    setFormData((prev) => ({
      ...prev,
      freezingSessionDate: date,
    }));
  };

  const isFormValid = formData.user && formData.device;

  return (
    <LocalizationProvider dateAdapter={AdapterDateFns}>
    <BaseFormDialog
      open={open}
      onClose={handleClose}
      title="Add New Freezing Session"
      onSave={handleSave}
      isSubmitting={isSubmitting}
      disabled={!isFormValid}
    >
      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
        <Box sx={{ display: 'flex', gap: 2 }}>
          <FormControl required sx={{ flex: 1 }}>
            <InputLabel id="user-label">User</InputLabel>
            <Select
              labelId="user-label"
              value={formData.user}
              onChange={(e) => handleInputChange('user', e.target.value)}
              label="User"
              sx={disabledTextFieldStyles}
              MenuProps={{
                PaperProps: {
                  style: {
                    maxHeight: 180,
                  },
                },
              }}
            >
              {users.length === 0 ? (
                <MenuItem value="" disabled>
                  No users available
                </MenuItem>
              ) : (
                users.map((user) => (
                  <MenuItem key={user.id} value={user.id}>
                    {user.full_name}
                  </MenuItem>
                ))
              )}
            </Select>
          </FormControl>

          <FormControl required sx={{ flex: 1 }}>
            <InputLabel id="device-label">Device</InputLabel>
            <Select
              labelId="device-label"
              value={formData.device}
              onChange={(e) => handleInputChange('device', e.target.value)}
              label="Device"
              sx={disabledTextFieldStyles}
              MenuProps={{
                PaperProps: {
                  style: {
                    maxHeight: 180,
                  },
                },
              }}
            >
              {devices.length === 0 ? (
                <MenuItem value="" disabled>
                  No devices available
                </MenuItem>
              ) : (
                devices.map((device) => (
                  <MenuItem key={device.id} value={device.id}>
                    {device.name}
                  </MenuItem>
                ))
              )}
            </Select>
          </FormControl>
        </Box>

        <Box sx={{ display: 'flex', gap: 2 }}>
          <TextField
            label="Device Temperature"
            placeholder="Enter temperature"
            type="number"
            value={formData.temperature}
            onChange={(e) => handleInputChange('temperature', e.target.value)}
            sx={{ ...disabledTextFieldStyles, flex: 1 }}
            InputProps={{
              endAdornment: <span style={{ color: '#666' }}>°C/F</span>,
            }}
          />
          <TextField
            label="Humidity"
            placeholder="Enter humidity"
            type="number"
            value={formData.humidity}
            onChange={(e) => handleInputChange('humidity', e.target.value)}
            sx={{ ...disabledTextFieldStyles, flex: 1 }}
            InputProps={{
              endAdornment: <span style={{ color: '#666' }}>%</span>,
            }}
          />
        </Box>
        <DateTimePicker
            label="Freezing Session Date"
            value={formData.freezingSessionDate || null}
            onChange={handleDateChange}
            slotProps={{
              textField: {
                required: false,
                sx: disabledTextFieldStyles,
                helperText: "Leave empty for today's date",
              },
            }}
          />

        <FormControl sx={{ flex: 1 }}>
          <InputLabel id="notes-page-label">Notes Page</InputLabel>
          <Select
            labelId="notes-page-label"
            value={formData.notesPage}
            onChange={(e) => handleInputChange('notesPage', e.target.value)}
            label="Notes Page"
            placeholder="Select notes page (optional)"
            sx={disabledTextFieldStyles}
            MenuProps={{
              PaperProps: {
                style: {
                  maxHeight: 180,
                },
              },
            }}
          >
            {notesPages.length === 0 ? (
              <MenuItem value="" disabled>
                No notes pages available
              </MenuItem>
            ) : (
              notesPages.map((page) => (
                <MenuItem key={page.id} value={page.id}>
                  {page.url}
                </MenuItem>
              ))
            )}
          </Select>
        </FormControl>
      </Box>
    </BaseFormDialog>
    </LocalizationProvider>
  );
};
