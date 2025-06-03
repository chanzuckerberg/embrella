import React from 'react';
import { FormControl, Select, MenuItem, IconButton, SelectChangeEvent } from '@mui/material';
import { Icon } from '@czi-sds/components';
import { METRICS_CONFIG } from '../constants/MetricConfig';

interface SortControlsProps {
  sortEnabled: boolean;
  sortBy: string;
  sortDirection: 'asc' | 'desc';
  onSortToggle: (event: React.ChangeEvent<HTMLInputElement>) => void;
  onSortByChange: (event: SelectChangeEvent) => void;
  onSortDirectionToggle: (direction: 'asc' | 'desc') => void;
}

/**
 * Component for rendering sort controls in the RawJson component
 */
export const SortControls: React.FC<SortControlsProps> = React.memo(
  ({ sortBy, sortDirection, onSortByChange, onSortDirectionToggle }) => (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        padding: '8px 16px',
        borderBottom: '1px solid #e0e0e0',
        backgroundColor: '#fafafa',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flexGrow: 1 }}>
        <div style={{ fontWeight: 500, marginRight: '8px' }}>Sort by:</div>

        <FormControl variant="outlined" size="small" sx={{ minWidth: 150 }}>
          <Select
            value={sortBy}
            onChange={onSortByChange}
            displayEmpty
            renderValue={(selected) => {
              if (selected === 'Select Metric') {
                return <em>Select metric</em>;
              }
              const selectedConfig = METRICS_CONFIG[selected as keyof typeof METRICS_CONFIG];
              return selectedConfig?.label || selected;
            }}
            inputProps={{ 'aria-label': 'Sort by' }}
          >
            <MenuItem value="Select Metric" disabled>
              <em>Select metric</em>
            </MenuItem>
            <MenuItem value="position_name">Position Name</MenuItem>
            {Object.entries(METRICS_CONFIG).map(([key, config]) => (
              <MenuItem key={key} value={key}>
                {config.label}
              </MenuItem>
            ))}
          </Select>
        </FormControl>

        <div style={{ display: 'flex', flexDirection: 'column' }}>
          <IconButton
            size="small"
            onClick={() => onSortDirectionToggle('asc')}
            title="Ascending"
            sx={{ padding: '2px' }}
          >
            <Icon color={sortDirection === 'asc' ? 'green' : 'gray'} sdsIcon="ChevronUp" sdsSize="xs" />
          </IconButton>
          <IconButton
            size="small"
            onClick={() => onSortDirectionToggle('desc')}
            title="Descending"
            sx={{ padding: '2px' }}
          >
            <Icon color={sortDirection === 'desc' ? 'green' : 'gray'} sdsIcon="ChevronDown" sdsSize="xs" />
          </IconButton>
        </div>
      </div>
    </div>
  )
);
SortControls.displayName = 'SortControls';
