import React, { useState, useEffect } from 'react';
import {
  Paper,
  Slider,
  Typography,
  TextField,
  FormControlLabel,
  Checkbox,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
} from '@mui/material';
import styles from './MetadataViz.module.css';
import { FilterConfig, MetricRanges } from '@app/common/types/metadataViz/metadataVizData';
import { Button } from '@czi-sds/components';
import { METRICS_CONFIG } from './constants/MetricConfig';

interface MetadataFilterRange {
  current: [number, number];
  min: number;
  max: number;
  enabled: boolean; //checkbox state
  histogramData?: number[];
}

type FilterState = {
  [K in keyof FilterConfig['filters']]: MetadataFilterRange;
};

interface MetadataFiltersProps {
  metricRanges: MetricRanges;
  onApplyFilters?: (filters: FilterConfig, selectedOption: string) => void;
}

export const MetadataFilters: React.FC<MetadataFiltersProps> = ({ metricRanges, onApplyFilters }) => {
  const [selectedOption, setSelectedOption] = useState('AND');

  // Initialize state with explicit number conversion
  const [filters, setFilters] = useState<FilterState>(() => {
    const initialState: FilterState = {} as FilterState;
    
    // Use METRICS_CONFIG keys which match FilterConfig
    Object.keys(METRICS_CONFIG).forEach((key) => {
      const metricKey = key as keyof typeof METRICS_CONFIG;
      if (metricRanges[metricKey] && Array.isArray(metricRanges[metricKey])) {
        initialState[metricKey] = {
          current: [Number(metricRanges[metricKey][0]), Number(metricRanges[metricKey][1])],
          min: Number(metricRanges[metricKey][0]),
          max: Number(metricRanges[metricKey][1]),
          enabled: true,
        };
      }
    });
    
    return initialState;
  });

  // Update filters when metric ranges change
  useEffect(() => {
    setFilters((prev) => {
      const newState = { ...prev };
      
      // Use METRICS_CONFIG keys which match FilterConfig
      Object.keys(METRICS_CONFIG).forEach((key) => {
        const metricKey = key as keyof typeof METRICS_CONFIG;
        if (metricRanges[metricKey]) {
          newState[metricKey] = {
            ...prev[metricKey],
            enabled: prev[metricKey]?.enabled ?? true,
          };
        }
      });
      
      return newState;
    });
  }, [metricRanges]);

  const handleSliderChange = (key: keyof FilterState) => (_: Event, newValue: number | number[]) => {
    if (!Array.isArray(newValue)) return;

    setFilters((prev) => ({
      ...prev,
      [key]: {
        ...prev[key],
        current: [Math.max(newValue[0], prev[key]?.min ?? 0), Math.min(newValue[1], prev[key]?.max ?? 100)],
      },
    }));
  };

  const handleCheckboxChange = (key: keyof FilterState) => (event: React.ChangeEvent<HTMLInputElement>) => {
    setFilters((prev) => ({
      ...prev,
      [key]: {
        ...prev[key],
        enabled: event.target.checked,
      },
    }));
  };

  const handleReset = () => {
    const resetState: FilterState = {} as FilterState;
    
    // Use METRICS_CONFIG keys which match FilterConfig
    Object.keys(METRICS_CONFIG).forEach((key) => {
      const metricKey = key as keyof typeof METRICS_CONFIG;
      if (metricRanges[metricKey] && Array.isArray(metricRanges[metricKey])) {
        resetState[metricKey] = {
          current: [Number(metricRanges[metricKey][0]), Number(metricRanges[metricKey][1])],
          min: Number(metricRanges[metricKey][0]),
          max: Number(metricRanges[metricKey][1]),
          enabled: true,
        };
      }
    });
    
    setFilters(resetState);
    setSelectedOption('AND');
  };

  const handleInputChange =
    (key: keyof FilterState, isMin: boolean) => (event: React.ChangeEvent<HTMLInputElement>) => {
      const value = Number(event.target.value);
      if (event.target.value === '' || isNaN(value)) return;

      setFilters((prev) => ({
        ...prev,
        [key]: {
          ...prev[key],
          current: isMin
            ? [Math.min(Math.max(value, prev[key]?.min ?? 0), prev[key]?.current[1] ?? 0), prev[key]?.current[1] ?? 0]
            : [prev[key]?.current[0] ?? 0, Math.min(Math.max(value, prev[key]?.current[0] ?? 0), prev[key]?.max ?? 0)],
        },
      }));
    };

  const handleApplyFilters = (state: FilterState, option: string) => {
    if (onApplyFilters) {
      // Check if any filters are enabled
      const hasEnabledFilters = Object.values(state).some((value) => value.enabled);

      const filterConfig: FilterConfig = {
        filters: hasEnabledFilters
          ? Object.entries(state).reduce(
              (acc, [key, value]) => {
                if (value.enabled) {
                  acc[key] = value.current;
                }
                return acc;
              },
              {} as Required<FilterConfig>['filters']
            )
          : {},
        filter_type: option as 'AND' | 'OR',
      };
      onApplyFilters(filterConfig, option);
    }
  };
  
  const renderFilter = (key: keyof FilterState) => {
    // Use the METRICS_CONFIG to get label and unit
    const config = METRICS_CONFIG[key as keyof typeof METRICS_CONFIG];
    const minValue = Number(filters[key]?.min ?? 0);
    const maxValue = Number(filters[key]?.max ?? 100);
    const current = filters[key]?.current ?? [minValue, maxValue];
    const currentMin = current[0];
    const currentMax = current[1];
    // Determine step value - use 0.1 for bad_patch metrics, otherwise calculate based on range
    const stepValue = key === 'bad_patch_low' || key === 'bad_patch_all' ? 0.1 : (maxValue - minValue) / 100;

    return (
      <div className={styles.filterRow}>
        <FormControlLabel
          control={<Checkbox checked={filters[key]?.enabled} onChange={handleCheckboxChange(key)} />}
          label={
            <Typography className={styles.filterLabel}>
              {config?.label} {config?.unit}
            </Typography>
          }
        />
        <div className={styles.filterContent}>
          <TextField
            size="small"
            value={currentMin}
            className={styles.minMaxInput}
            onChange={(e) => handleInputChange(key, true)(e as React.ChangeEvent<HTMLInputElement>)}
            inputProps={{
              className: styles.input,
              type: 'number',
              min: minValue,
              max: maxValue,
              step: stepValue,
            }}
          />
          <Slider
            value={[currentMin, currentMax]}
            onChange={handleSliderChange(key)}
            min={minValue}
            max={maxValue}
            step={stepValue}
            className={styles.slider}
            disabled={!filters[key]?.enabled}
            valueLabelDisplay="auto"
          />
          <TextField
            size="small"
            value={currentMax}
            className={styles.minMaxInput}
            onChange={(e) => handleInputChange(key, false)(e as React.ChangeEvent<HTMLInputElement>)}
            inputProps={{
              className: styles.input,
              type: 'number',
              min: minValue,
              max: maxValue,
              step: stepValue,
            }}
          />
        </div>
      </div>
    );
  };

  return (
    <Paper className={styles.filterPaper} elevation={1}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <Typography variant="h1">Filters</Typography>
        <FormControl style={{ minWidth: 100 }}>
          <InputLabel sx={{ backgroundColor: 'white', padding: '0 4px' }}>Filter Type</InputLabel>
          <Select
            label="Filter Type"
            value={selectedOption}
            onChange={(e) => setSelectedOption(e.target.value as 'AND' | 'OR')}
            size="small"
          >
            <MenuItem value="AND">AND</MenuItem>
            <MenuItem value="OR">OR</MenuItem>
          </Select>
        </FormControl>
      </div>

      {Object.keys(filters).map((key) => renderFilter(key as keyof FilterState))}
      <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '20px' }}>
        <Button sdsType="secondary" sdsStyle="rounded" onClick={handleReset}>
          Reset
        </Button>
        <Button sdsType="primary" sdsStyle="rounded" onClick={() => handleApplyFilters(filters, selectedOption)}>
          Apply Filter
        </Button>
      </div>
    </Paper>
  );
};