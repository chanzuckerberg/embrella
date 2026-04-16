'use client';

import React from 'react';
import { Box, MenuItem, FormControl, InputLabel, Select, IconButton } from '@mui/material';
import { Icon } from '@czi-sds/components';
import { disabledTextFieldStyles } from '@app/components/GridsLogging/GridBox/DisableBoxStyle';

interface FormFieldWithAddProps {
  label: string;
  value: string;
  onChange: (value: string) => void;
  onAdd?: () => void;
  required?: boolean;
  disabled?: boolean;
  options?: Array<{ value: string; label: string }>;
  placeholder?: string;
  flex?: number;
}

export const FormFieldWithAdd: React.FC<FormFieldWithAddProps> = ({
  label,
  value,
  onChange,
  onAdd,
  required = false,
  disabled = false,
  options = [],
  placeholder: _placeholder,
  flex = 1, // Default to flex: 1
}) => {
  return (
    <Box sx={{ display: 'flex', gap: 2, alignItems: 'flex-start', flex: flex, minWidth: 0 }}>
      <FormControl required={required} sx={{ flex: 1, minWidth: 0 }}>
        <InputLabel>{label}</InputLabel>
        <Select
          value={value}
          onChange={(e) => onChange(e.target.value)}
          label={label}
          disabled={disabled}
          sx={{
            ...disabledTextFieldStyles,
            '& .MuiSelect-select': {
              whiteSpace: 'normal',
              wordBreak: 'break-word',
            },
          }}
          MenuProps={{
            PaperProps: {
              style: {
                maxHeight: 180,
              },
            },
          }}
        >
          <MenuItem value="">Select {label}</MenuItem>
          {options.map((option) => (
            <MenuItem key={option.value} value={option.value}>
              {option.label}
            </MenuItem>
          ))}
        </Select>
      </FormControl>
      {onAdd && (
        <IconButton
          onClick={onAdd}
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
      )}
    </Box>
  );
};
