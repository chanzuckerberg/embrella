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
  onApplyFilters?: (filters: FilterConfig, selectedOption: 'AND' | 'OR') => void;
}

export const MetadataFilters: React.FC<MetadataFiltersProps> = ({ metricRanges, onApplyFilters }) => {
  const [selectedOption, setSelectedOption] = useState<'AND' | 'OR'>('AND');
  const [inputValues, setInputValues] = useState<Record<string, { min: string; max: string }>>({});
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

  // Helper function to create a filter range object
  const createFilterRange = (
    metricKey: keyof typeof METRICS_CONFIG,
    range: [number, number] | undefined,
    prevState: FilterState
  ): MetadataFilterRange => {
    const currentRange: [number, number] = Array.isArray(range)
      ? [Number(range[0]), Number(range[1])]
      : prevState[metricKey]?.current || [0, 100];

    return {
      ...prevState[metricKey],
      current: currentRange,
      min: Number(Array.isArray(range) ? range[0] : prevState[metricKey]?.min || 0),
      max: Number(Array.isArray(range) ? range[1] : prevState[metricKey]?.max || 100),
      enabled: prevState[metricKey]?.enabled ?? true,
    };
  };

  // Update filters when metric ranges change
  useEffect(() => {
    setFilters((prev) => {
      const newState = { ...prev };
      // Use METRICS_CONFIG keys which match FilterConfig
      Object.keys(METRICS_CONFIG).forEach((key) => {
        const metricKey = key as keyof typeof METRICS_CONFIG;
        if (metricRanges[metricKey]) {
          newState[metricKey] = createFilterRange(metricKey, metricRanges[metricKey], prev);
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
    const resetInputValues: Record<string, { min: string; max: string }> = {};
    
    // Use METRICS_CONFIG keys which match FilterConfig
    Object.keys(METRICS_CONFIG).forEach((key) => {
      const metricKey = key as keyof typeof METRICS_CONFIG;
      if (metricRanges[metricKey] && Array.isArray(metricRanges[metricKey])) {
        // Reset filter state
        resetState[metricKey] = {
          current: [Number(metricRanges[metricKey][0]), Number(metricRanges[metricKey][1])],
          min: Number(metricRanges[metricKey][0]),
          max: Number(metricRanges[metricKey][1]),
          enabled: true,
        };
        
        // Reset input values state
        resetInputValues[metricKey] = {
          min: Number(metricRanges[metricKey][0]).toFixed(3),
          max: Number(metricRanges[metricKey][1]).toFixed(3),
        };
      }
    });
    
    // Update both states
    setFilters(resetState);
    setInputValues(resetInputValues);
    setSelectedOption('AND');
    
    const emptyFilterConfig: FilterConfig = {
      filters: {},
      filter_type: 'AND',
    };
    
    // Also apply the reset filters to update the scatter plot
    if (onApplyFilters) {
      onApplyFilters(emptyFilterConfig, 'AND');
    }
  };

  // Helper function to update input values state
  const updateInputValues = (key: keyof FilterState, isMin: boolean, value: string) => {
    setInputValues((prev) => ({
      ...prev,
      [key]: {
        ...(prev[key] || {
          min: filters[key]?.current[0].toString(),
          max: filters[key]?.current[1].toString(),
        }),
        [isMin ? 'min' : 'max']: value,
      },
    }));
  };

  // Helper function to get constrained value
  const getConstrainedValue = (value: number, min: number, max: number): number => {
    return Number(Math.min(Math.max(value, min), max).toFixed(3));
  };

  // Helper function to calculate the new current value
  const calculateCurrentValue = (
    formattedValue: number,
    key: keyof FilterState,
    isMin: boolean,
    prevState: FilterState
  ): [number, number] => {
    if (isMin) {
      const min = prevState[key]?.min ?? 0;
      const currentMax = prevState[key]?.current[1] ?? 0;
       // Don't constrain the value when typing - only ensure it doesn't exceed max
       const constrainedMin = Math.min(formattedValue, currentMax);
      return [constrainedMin, currentMax];
    } else {
      const currentMin = prevState[key]?.current[0] ?? 0;
      const max = prevState[key]?.max ?? 0;
 // Don't constrain the value when typing - only ensure it doesn't go below min
 const constrainedMax = Math.max(formattedValue, max);
      return [currentMin, constrainedMax];
    }
  };

  // Handle input change with reduced complexity
  const handleInputChange =
    (key: keyof FilterState, isMin: boolean) => (event: React.ChangeEvent<HTMLInputElement>) => {
      const inputValue = event.target.value;

      // Update the input value state
      updateInputValues(key, isMin, inputValue);

      // If empty, allow the field to be empty but don't update filter state
      if (inputValue === '') {
        return;
      }

      const value = Number(inputValue);
      if (isNaN(value)) {
        return;
      }

      // Apply 3 decimal precision
      const formattedValue = Number(value.toFixed(3));

      // Update filters state
      setFilters((prev) => ({
        ...prev,
        [key]: {
          ...prev[key],
          current: calculateCurrentValue(formattedValue, key, isMin, prev),
        },
      }));
    };

  const handleInputBlur = (key: keyof FilterState, isMin: boolean) => () => {
    setInputValues((prev) => {
      const currentKey = prev[key] || { min: '', max: '' };
      const currentValue = currentKey[isMin ? 'min' : 'max'];

      // If the input is empty or invalid on blur, reset to the current filter value
      if (currentValue === '' || isNaN(Number(currentValue))) {
        return {
          ...prev,
          [key]: {
            ...currentKey,
            [isMin ? 'min' : 'max']: filters[key]?.current[isMin ? 0 : 1].toFixed(3),
          },
        };
      }

      // Otherwise, format the valid number to 3 decimal places
      return {
        ...prev,
        [key]: {
          ...currentKey,
          [isMin ? 'min' : 'max']: Number(currentValue).toFixed(3),
        },
      };
    });
  };

  const handleApplyFilters = (state: FilterState, option: 'AND' | 'OR') => {
    if (onApplyFilters) {
      // Check if any filters are enabled
      const hasEnabledFilters = Object.values(state).some((value) => value.enabled);

      const filterConfig: FilterConfig = {
        filters: hasEnabledFilters
          ? Object.entries(state).reduce(
              (acc, [key, value]) => {
                if (value.enabled) {
                  const metricKey = key as keyof FilterConfig['filters'];
                  acc[metricKey] = value.current;
                }
                return acc;
              },
              {} as Required<FilterConfig>['filters']
            )
          : {},
        filter_type: option,
      };
      onApplyFilters(filterConfig, option);
    }
  };

  // Add a new handler for unchecking all filters
  const handleUncheckAll = () => {
    setFilters((prev) => {
      const newState = { ...prev };
      Object.keys(newState).forEach((key) => {
        const metricKey = key as keyof FilterState;
        newState[metricKey] = {
          ...newState[metricKey],
          enabled: false,
        } as MetadataFilterRange;
      });
      return newState;
    });
  };

  // Helper function to determine step value based on metric key and range
  const getStepValue = (key: keyof FilterState, minValue: number, maxValue: number) => {
    return key === 'bad_patch_low' || key === 'bad_patch_all' ? 0.1 : (maxValue - minValue) / 100;
  };

  const renderFilterLabel = (key: keyof FilterState, config: (typeof METRICS_CONFIG)[keyof typeof METRICS_CONFIG]) => {
    return (
      <FormControlLabel
        control={<Checkbox checked={filters[key]?.enabled} onChange={handleCheckboxChange(key)} />}
        label={
          <Typography className={styles.filterLabel}>
            {config?.label} {config?.unit}
          </Typography>
        }
      />
    );
  };

  const renderInputField = (
    key: keyof FilterState,
    value: number,
    isMin: boolean,
    minValue: number,
    maxValue: number,
    stepValue: number
  ) => {
    // Get the current input value from state or use the provided value
    const inputValue =
      inputValues[key as string]?.[isMin ? 'min' : 'max'] !== undefined
        ? inputValues[key as string]?.[isMin ? 'min' : 'max']
        : value.toFixed(3);

    return (
      <TextField
        size="small"
        value={inputValue}
        className={styles.minMaxInput}
        onChange={(e) => handleInputChange(key, isMin)(e as React.ChangeEvent<HTMLInputElement>)}
        onBlur={handleInputBlur(key, isMin)}
        inputProps={{
          className: styles.input,
          min: minValue,
          max: maxValue,
          step: stepValue,
        }}
      />
    );
  };

  const renderSlider = (
    key: keyof FilterState,
    currentMin: number,
    currentMax: number,
    minValue: number,
    maxValue: number,
    stepValue: number
  ) => {
    return (
      <Slider
        value={[currentMin, currentMax]}
        onChange={handleSliderChange(key)}
        min={minValue}
        max={maxValue}
        step={stepValue}
        className={styles.slider}
        disabled={!filters[key]?.enabled}
        valueLabelDisplay="auto"
        valueLabelFormat={(value) => value.toFixed(3)}
      />
    );
  };

  const renderFilter = (key: keyof FilterState) => {
    // Use the METRICS_CONFIG to get label and unit
    const config = METRICS_CONFIG[key as keyof typeof METRICS_CONFIG];
    const minValue = Number(filters[key]?.min ?? 0);
    const maxValue = Number(filters[key]?.max ?? 100);
    const current = filters[key]?.current ?? [minValue, maxValue];
    const currentMin = Number(current[0].toFixed(3));
    const currentMax = Number(current[1].toFixed(3));

    // Get step value using helper function
    const stepValue = getStepValue(key, minValue, maxValue);

    return (
      <div className={styles.filterRow} key={`filter-${key}`}>
        {renderFilterLabel(key, config)}
        <div className={styles.filterContent}>
          {renderInputField(key, currentMin, true, minValue, maxValue, stepValue)}
          {renderSlider(key, currentMin, currentMax, minValue, maxValue, stepValue)}
          {renderInputField(key, currentMax, false, minValue, maxValue, stepValue)}
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
        <Button sdsType="secondary" sdsStyle="rounded" onClick={handleUncheckAll}>
          Uncheck All
        </Button>
        <Button sdsType="primary" sdsStyle="rounded" onClick={() => handleApplyFilters(filters, selectedOption)}>
          Apply Filter
        </Button>
      </div>
    </Paper>
  );
};