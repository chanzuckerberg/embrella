'use client';

import React, { useState } from 'react';
import { TextField } from '@mui/material';
import { BaseFormDialog } from './BaseFormDialog';
import { disabledTextFieldStyles } from '@app/components/GridsLogging/GridBox/DisableBoxStyle';

interface AddItemDialogProps {
  open: boolean;
  onClose: () => void;
  title: string;
  fieldLabel: string;
  fieldPlaceholder: string;
  onSave: (value: string) => void;
}

export const AddItemDialog: React.FC<AddItemDialogProps> = ({
  open,
  onClose,
  title,
  fieldLabel,
  fieldPlaceholder,
  onSave
}) => {
  const [value, setValue] = useState('');

  const handleSave = () => {
    if (value.trim()) {
      onSave(value.trim());
      setValue('');
      onClose();
    }
  };

  return (
    <BaseFormDialog
      open={open}
      onClose={onClose}
      title={title}
      onSave={handleSave}
      disabled={!value.trim()}
    >
      <TextField
        required
        label={fieldLabel}
        placeholder={fieldPlaceholder}
        value={value}
        onChange={(e) => setValue(e.target.value)}
        sx={disabledTextFieldStyles}
      />
    </BaseFormDialog>
  );
};