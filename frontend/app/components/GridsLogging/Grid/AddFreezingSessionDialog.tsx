'use client';

import React, { useState } from 'react';
import { Box, TextField } from '@mui/material';
import { BaseFormDialog } from '@app/common/components/Forms/BaseFormDialog';
import { disabledTextFieldStyles } from '@app/components/GridsLogging/GridBox/DisableBoxStyle';
import { Device, UserList, FreezingSessionFormData, ExternalResource } from '@app/common/types/gridLogging';
import { FormFieldWithAdd } from '@app/common/components/Forms/FormFieldWithAdd';
import { CreateNotesPageDialog } from '@app/components/GridsLogging/Grid/CreateNotesPageDialog';
import { DateTimePicker } from '@mui/x-date-pickers/DateTimePicker';
import { LocalizationProvider } from '@mui/x-date-pickers/LocalizationProvider';
import { AdapterDateFns } from '@mui/x-date-pickers/AdapterDateFns';

export const AddFreezingSessionDialog: React.FC<{
  open: boolean;
  onClose: () => void;
  onSave: (data: FreezingSessionFormData) => void;
  users?: UserList[];
  devices?: Device[];
  notesPages?: ExternalResource[];
  freezingSessionDate?: Date | null;
  refetchNotesPages?: () => void;
}> = ({
  open,
  onClose,
  onSave,
  users = [],
  devices = [],
  notesPages = [],
  freezingSessionDate: _freezingSessionDate = null,
  refetchNotesPages,
}) => {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [addNoteDialogOpen, setAddNoteDialogOpen] = useState(false);
  const [formData, setFormData] = useState<FreezingSessionFormData>({
    user: '',
    device: '',
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
    if (!formData.user || !formData.device) {
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
            <FormFieldWithAdd
              label="User"
              required
              value={formData.user}
              onChange={(value) => handleInputChange('user', value)}
              options={users.map((user) => ({ value: String(user.id), label: user.full_name }))}
            />
            <FormFieldWithAdd
              label="Device"
              required
              value={formData.device}
              onChange={(value) => handleInputChange('device', value)}
              options={devices.map((device) => ({ value: String(device.id), label: device.name }))}
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

          <FormFieldWithAdd
            label="Notes Page"
            placeholder="Select notes page (optional)"
            value={formData.notesPage}
            onChange={(value) => handleInputChange('notesPage', value)}
            options={notesPages.map((page) => ({
              value: String(page.id),
              label: page.system_name ? `${page.name} (${page.system_name})` : page.name || page.url,
            }))}
            onAdd={() => setAddNoteDialogOpen(true)}
          />
        </Box>
      </BaseFormDialog>

      <CreateNotesPageDialog
        open={addNoteDialogOpen}
        onClose={() => setAddNoteDialogOpen(false)}
        onSave={(resource) => {
          refetchNotesPages?.();
          setFormData((prev) => ({ ...prev, notesPage: String(resource.id) }));
          setAddNoteDialogOpen(false);
        }}
      />
    </LocalizationProvider>
  );
};
