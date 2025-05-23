import React, { useState } from 'react';
import ReactJson from 'react-json-view';
import styles from './MetadataViz.module.css';
import {
  Card,
  CardHeader,
  FormControlLabel,
  Switch,
  Select,
  MenuItem,
  FormControl,
  IconButton,
  SelectChangeEvent,
} from '@mui/material';
import { Icon } from '@czi-sds/components';
import { METRICS_CONFIG } from './constants/MetricConfig';
import { MetadataVizResponse } from '@app/common/types/metadataViz/metadataVizData';

interface RawJsonProps {
  isOpen: boolean;
  onClose: () => void;
  data?: MetadataVizResponse;
}

export const RawJson: React.FC<RawJsonProps> = ({ isOpen, onClose, data }) => {
  // Sorting state
  const [sortEnabled, setSortEnabled] = useState<boolean>(false);
  const [sortBy, setSortBy] = useState<string>('Select Metric');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc');

  // Create a JSON representation with accepted position names and filtering ranges
  const createFocusedJson = () => {
    if (!data) return {};

    // Get position names from accepted results
    let positionNames = data.accepted_results?.map((item) => item.name) || [];

    // Apply sorting if enabled
    if (sortEnabled && positionNames.length > 0) {
      positionNames = positionNames.sort((a, b) => {
        const comparison = a.localeCompare(b);
        return sortDirection === 'asc' ? comparison : -comparison;
      });
    }

    // Get filtering ranges from filters_applied
    const filterRanges: Record<string, string> = {};

    if (data.filters_applied?.filters) {
      // Convert filter ranges to readable format
      Object.entries(data.filters_applied.filters).forEach(([key, range]) => {
        if (Array.isArray(range) && range.length === 2) {
          // Get unit from METRICS_CONFIG
          const metricConfig = METRICS_CONFIG[key as keyof typeof METRICS_CONFIG];
          const unit = metricConfig?.unit || '';
          const label = metricConfig?.label || key;

          // Fix decimal places to 2 for better readability
          const minValue = Number(range[0]).toFixed(2);
          const maxValue = Number(range[1]).toFixed(2);

          filterRanges[label] = `${minValue}-${maxValue}${unit}`;
        }
      });
    }

    return {
      'Selected positions': positionNames,
      'Filtering ranges': filterRanges,
      'Filter type': data.filters_applied?.filter_type || 'None',
    };
  };

  const jsonData = createFocusedJson();

  const handleCopy = () => {
    const jsonString = JSON.stringify(jsonData, null, 2);
    navigator.clipboard.writeText(jsonString);
  };

  const handleDownload = () => {
    const jsonString = JSON.stringify(jsonData, null, 2);
    const blob = new Blob([jsonString], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'Metadata.json';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const handleSortToggle = (event: React.ChangeEvent<HTMLInputElement>) => {
    setSortEnabled(event.target.checked);
  };

  const handleSortByChange = (event: SelectChangeEvent) => {
    setSortBy(event.target.value);
  };

  const handleSortDirectionToggle = () => {
    setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
  };

  return (
    <div className={`${styles.sidebar} ${isOpen ? styles.open : ''}`}>
      <div className={styles.sidebarContent}>
        <Card elevation={2}>
          <CardHeader
            title="Raw JSON"
            sx={{
              backgroundColor: '#f5f5f5',
              borderBottom: '1px solid #e0e0e0',
            }}
            action={
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <FormControlLabel
                  control={<Switch checked={sortEnabled} onChange={handleSortToggle} color="primary" size="small" />}
                  label="Sort"
                  sx={{ marginRight: 0 }}
                />
                <IconButton size="small" onClick={handleCopy} title="Copy JSON" sx={{ padding: '4px' }}>
                  <Icon color="green" sdsIcon="Copy" sdsSize="s" />
                </IconButton>
                <IconButton size="small" onClick={handleDownload} title="Download JSON" sx={{ padding: '4px' }}>
                  <Icon color="green" sdsIcon="Download" sdsSize="s" />
                </IconButton>
                <IconButton size="small" onClick={onClose} title="Close" sx={{ padding: '4px' }}>
                  <Icon color="green" sdsIcon="XMark" sdsSize="s" />
                </IconButton>
              </div>
            }
          />

          {/* Sort controls row - only visible when sorting is enabled */}
          {sortEnabled && (
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
                    onChange={handleSortByChange}
                    displayEmpty
                    renderValue={(selected) => {
                      if (selected === '') {
                        return <em>Select metric</em>;
                      }
                      const selectedConfig = METRICS_CONFIG[selected as keyof typeof METRICS_CONFIG];
                      return selectedConfig?.label || selected;
                    }}
                    inputProps={{ 'aria-label': 'Sort by' }}
                  >
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
                    onClick={() => setSortDirection('asc')}
                    title="Ascending"
                    sx={{
                      padding: '2px',
                    }}
                  >
                    <Icon color={sortDirection === 'asc' ? 'green' : 'gray'} sdsIcon="ChevronUp" sdsSize="xs" />
                  </IconButton>
                  <IconButton
                    size="small"
                    onClick={() => setSortDirection('desc')}
                    title="Descending"
                    sx={{
                      padding: '2px',
                    }}
                  >
                    <Icon color={sortDirection === 'desc' ? 'green' : 'gray'} sdsIcon="ChevronDown" sdsSize="xs" />
                  </IconButton>
                </div>
              </div>
            </div>
          )}

          <div className={styles.jsonContainer}>
            <ReactJson
              src={jsonData}
              theme="monokai"
              displayDataTypes={false}
              enableClipboard={false}
              collapsed={1}
              style={{ padding: 15 }}
            />
          </div>
        </Card>
      </div>
    </div>
  );
};
