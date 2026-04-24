'use client';

import React from 'react';
import { Box, TextField, Autocomplete, IconButton } from '@mui/material';
import SearchIcon from '@mui/icons-material/Search';
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
  placeholder,
  flex = 1,
}) => {
  const selectedOption = options.find((option) => option.value === value) ?? null;

  return (
    <Box sx={{ display: 'flex', gap: 2, alignItems: 'flex-start', flex: flex, minWidth: 0 }}>
      <Autocomplete
        sx={{
          flex: 1,
          minWidth: 0,
          ...disabledTextFieldStyles,
          '& .MuiAutocomplete-popupIndicator': { transform: 'none' },
        }}
        options={options}
        value={selectedOption}
        onChange={(_event, newValue) => onChange(newValue?.value ?? '')}
        getOptionLabel={(option) => option.label}
        getOptionKey={(option) => option.value}
        isOptionEqualToValue={(option, val) => option.value === val.value}
        disabled={disabled}
        clearOnEscape
        popupIcon={<SearchIcon fontSize="small" />}
        renderInput={(params) => <TextField {...params} label={label} required={required} placeholder={placeholder} />}
      />
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
