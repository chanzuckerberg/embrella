'use client';

import React from 'react';
import { Autocomplete, Box, Chip, Paper, PaperProps, SxProps, TextField, Theme } from '@mui/material';
import SearchIcon from '@mui/icons-material/Search';
import { Icon } from '@czi-sds/components';
import { Sample } from '@app/common/types/gridLogging';
import { useSampleList } from '@app/common/hooks/useGridLogging';
import { disabledTextFieldStyles } from '@app/components/GridsLogging/GridBox/DisableBoxStyle';

interface SamplesAutocompleteProps {
  value: Sample[];
  onChange: (samples: Sample[]) => void;
  onAddNew: () => void;
  disabled?: boolean;
  required?: boolean;
  sx?: SxProps<Theme>;
}

export const SamplesAutocomplete: React.FC<SamplesAutocompleteProps> = ({
  value,
  onChange,
  onAddNew,
  disabled = false,
  required = false,
  sx,
}) => {
  const { transformedSamples } = useSampleList();

  const selectedIds = new Set(value.map((s) => s.id));
  const options = transformedSamples.filter((s) => !selectedIds.has(s.id));

  const DropdownPaper = (paperProps: PaperProps) => (
    <Paper {...paperProps}>
      <Box
        onMouseDown={(e) => {
          // Prevent Autocomplete blur before onClick fires
          e.preventDefault();
          onAddNew();
        }}
        sx={{
          display: 'flex',
          alignItems: 'center',
          gap: 1,
          px: 2,
          py: 1,
          cursor: 'pointer',
          color: 'primary.main',
          borderBottom: '1px solid',
          borderColor: 'divider',
          fontSize: 14,
          fontWeight: 500,
          '&:hover': { backgroundColor: 'action.hover' },
        }}
      >
        <Icon sdsIcon="Plus" sdsSize="s" />
        Add New Sample
      </Box>
      {paperProps.children}
    </Paper>
  );

  return (
    <Box sx={{ display: 'flex', gap: 2, alignItems: 'flex-start' }}>
      <Autocomplete
        multiple
        disableCloseOnSelect
        disabled={disabled}
        options={options}
        value={value}
        getOptionLabel={(option) => (option.ontology ? `${option.name} (${option.ontology})` : option.name)}
        isOptionEqualToValue={(option, val) => option.id === val.id}
        onChange={(_event, newValue) => onChange(newValue as Sample[])}
        PaperComponent={DropdownPaper}
        popupIcon={<SearchIcon fontSize="small" />}
        renderTags={(tagValue, getTagProps) =>
          tagValue.map((sample, index) => {
            const { onDelete, ...tagProps } = getTagProps({ index });
            return (
              <Chip
                {...tagProps}
                {...(!disabled ? { onDelete } : {})}
                key={sample.id}
                label={sample.name}
                size="small"
                sx={{
                  backgroundColor: '#6E4FF9 !important',
                  color: '#fff',
                  fontWeight: 500,
                  height: 22,
                  fontSize: 12,
                  borderRadius: '4px',
                  '& .MuiChip-label': { px: '6px', color: '#fff' },
                  '& .MuiChip-deleteIcon': {
                    color: 'rgba(255,255,255,0.7)',
                    fontSize: 16,
                    '&:hover': { color: '#fff' },
                  },
                }}
              />
            );
          })
        }
        renderInput={(params) => (
          <TextField
            {...params}
            label="Samples Present on Grid"
            required={required}
            placeholder={value.length === 0 ? 'Select sample(s)' : ''}
            sx={disabledTextFieldStyles}
          />
        )}
        ListboxProps={{ sx: { maxHeight: 200 } }}
        sx={{ flex: 1, '& .MuiAutocomplete-popupIndicator': { transform: 'none' }, ...sx }}
      />
    </Box>
  );
};
