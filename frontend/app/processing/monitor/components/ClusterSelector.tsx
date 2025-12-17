'use client';

import { FormControl, InputLabel, Select, MenuItem, SelectChangeEvent } from '@mui/material';

interface ClusterSelectorProps {
  value: 'czii' | 'bruno';
  onChange: (cluster: 'czii' | 'bruno') => void;
}

export const ClusterSelector: React.FC<ClusterSelectorProps> = ({ value, onChange }) => {
  const handleChange = (event: SelectChangeEvent) => {
    onChange(event.target.value as 'czii' | 'bruno');
  };

  return (
    <FormControl size="small" sx={{ minWidth: 150 }}>
      <InputLabel id="cluster-select-label">Cluster</InputLabel>
      <Select labelId="cluster-select-label" id="cluster-select" value={value} label="Cluster" onChange={handleChange}>
        <MenuItem value="czii">CZII</MenuItem>
        <MenuItem value="bruno">Bruno</MenuItem>
      </Select>
    </FormControl>
  );
};
