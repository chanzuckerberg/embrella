import React from 'react';
import { Typography, FormControl, InputLabel, Select, MenuItem } from '@mui/material';

interface FilterHeaderProps {
  selectedOption: 'AND' | 'OR';
  onOptionChange: (option: 'AND' | 'OR') => void;
}

export const FilterHeader: React.FC<FilterHeaderProps> = ({ selectedOption, onOptionChange }) => {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
      <Typography variant="h1">Filters</Typography>
      <FormControl style={{ minWidth: 100 }}>
        <InputLabel sx={{ backgroundColor: 'white', padding: '0 4px' }}>Filter Type</InputLabel>
        <Select
          label="Filter Type"
          value={selectedOption}
          onChange={(e) => onOptionChange(e.target.value as 'AND' | 'OR')}
          size="small"
        >
          <MenuItem value="AND">AND</MenuItem>
          <MenuItem value="OR">OR</MenuItem>
        </Select>
      </FormControl>
    </div>
  );
};
