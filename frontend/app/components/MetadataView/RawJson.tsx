'use client';
import React, { useState, useEffect } from 'react';
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
import { API, DJANGO_URL } from '@app/common/constants/api';

interface RawJsonProps {
  isOpen: boolean;
  onClose: () => void;
  data?: MetadataVizResponse;
  onSortChange?: (sortBy: string, sortDirection: 'asc' | 'desc') => void;
}

export const RawJson: React.FC<RawJsonProps> = ({ isOpen, onClose, data, onSortChange }) => {
  // Sorting state
  const [sortEnabled, setSortEnabled] = useState<boolean>(false);
  const [sortBy, setSortBy] = useState<string>('Select Metric');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc');
  const [sortedData, setSortedData] = useState<MetadataVizResponse | undefined>(data);
  const [isLoading, setIsLoading] = useState<boolean>(false);

  // Update sortedData when data prop changes
  useEffect(() => {
    setSortedData(data);
  }, [data]);

  // Fetch sorted data when sorting parameters change
  useEffect(() => {
    const fetchSortedData = async () => {
      // Only fetch if sorting is enabled and a valid metric is selected
      if (!sortEnabled || !sortBy || sortBy === 'Select Metric' || !data) {
        setSortedData(data);
        return;
      }

      try {
        setIsLoading(true);

        // Build the API URL with sorting parameters
        let url = `${DJANGO_URL}${API.METADATA_VIZ}?session_name=${data.session_name}&run_number=${data.run_number}`;

        // Add filters if present
        if (data.filters_applied && data.filters_applied.filters) {
          const filterConfig = {
            filter_type: data.filters_applied.filter_type,
            filters: data.filters_applied.filters,
          };
          url += `&q=${encodeURIComponent(JSON.stringify(filterConfig))}`;
        }

        // Add sorting parameters
        url += `&sort_by=${encodeURIComponent(sortBy)}&sort_direction=${encodeURIComponent(sortDirection)}`;

        const response = await fetch(url);

        if (!response.ok) {
          throw new Error('Failed to fetch sorted data');
        }

        const jsonData = await response.json();
        setSortedData(jsonData);

        // Still call onSortChange if provided (for backward compatibility)
        if (onSortChange) {
          onSortChange(sortBy, sortDirection);
        }
      } catch (error) {
        console.error('Error fetching sorted data:', error);
        // Fallback to client-side sorting if API call fails
        if (data) {
          const clientSortedData = { ...data };
          if (clientSortedData.accepted_results) {
            clientSortedData.accepted_results = [...clientSortedData.accepted_results].sort((a, b) => {
              const aValue = a.metrics[sortBy as keyof typeof a.metrics] || 0;
              const bValue = b.metrics[sortBy as keyof typeof b.metrics] || 0;
              return sortDirection === 'asc' ? aValue - bValue : bValue - aValue;
            });
          }
          setSortedData(clientSortedData);
        }
      } finally {
        setIsLoading(false);
      }
    };

    fetchSortedData();
  }, [sortEnabled, sortBy, sortDirection, data, onSortChange]);

  // Create a JSON representation with accepted position names and filtering ranges
  const createFocusedJson = () => {
    if (!sortedData) return {};

    // Get position names from accepted results
    let positionNames = sortedData.accepted_results?.map((item) => item.name) || [];

    // Apply client-side sorting for position names if no metric is selected
    if (sortEnabled && sortBy === 'Select Metric' && positionNames.length > 0) {
      positionNames = positionNames.sort((a, b) => {
        const comparison = a.localeCompare(b);
        return sortDirection === 'asc' ? comparison : -comparison;
      });
    }

    // Get filtering ranges from filters_applied
    const filterRanges: Record<string, string> = {};

    if (sortedData.filters_applied?.filters) {
      // Convert filter ranges to readable format
      Object.entries(sortedData.filters_applied.filters).forEach(([key, range]) => {
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
      'Filter type': sortedData.filters_applied?.filter_type || 'None',
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

  const handleSortDirectionToggle = (newDirection: 'asc' | 'desc') => {
    setSortDirection(newDirection);
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
                    onClick={() => handleSortDirectionToggle('asc')}
                    title="Ascending"
                    sx={{
                      padding: '2px',
                    }}
                  >
                    <Icon color={sortDirection === 'asc' ? 'green' : 'gray'} sdsIcon="ChevronUp" sdsSize="xs" />
                  </IconButton>
                  <IconButton
                    size="small"
                    onClick={() => handleSortDirectionToggle('desc')}
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
            {isLoading ? (
              <div style={{ padding: 15, textAlign: 'center' }}>Loading...</div>
            ) : (
              <ReactJson
                src={jsonData}
                theme="monokai"
                displayDataTypes={false}
                enableClipboard={false}
                collapsed={1}
                style={{ padding: 15 }}
              />
            )}
          </div>
        </Card>
      </div>
    </div>
  );
};
