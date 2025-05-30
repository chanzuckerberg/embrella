import React, { useState, useEffect } from 'react';
import { Paper } from '@mui/material';
import styles from './MetadataViz.module.css';
import { FilterConfig, MetricRanges } from '@app/common/types/metadataViz/metadataVizData';
import { METRICS_CONFIG } from './constants/MetricConfig';
import { MetadataSummaryResponse } from '@app/common/types/metadataViz/metadataSummary';
import { FilterHeader } from './filter/FilterHeader';
import { FilterItem } from './filter/FilterItem';
import { FilterControls } from './filter/FilterControls';
import { createInitialFilterState, createFilterRange, createEmptyFilterConfig } from './utils/FilterUtils';
import { FilterState, MetadataFilterRange } from '@app/common/types/metadataViz/FilterType';
import { asMetricKey } from './utils/FilterUtils';

interface MetadataFiltersProps {
  metricRanges: MetricRanges;
  onApplyFilters?: (filters: FilterConfig, selectedOption: 'AND' | 'OR') => void;
  summaryAPIData?: MetadataSummaryResponse;
}

export const MetadataFilters: React.FC<MetadataFiltersProps> = ({ metricRanges, onApplyFilters, summaryAPIData }) => {
  const [selectedOption, setSelectedOption] = useState<'AND' | 'OR'>('AND');
  const [inputValues, setInputValues] = useState<Record<string, { min: string; max: string }>>({});
  const [filters, setFilters] = useState<FilterState>(() => createInitialFilterState(metricRanges, METRICS_CONFIG));

  // Update filters when metric ranges change
  useEffect(() => {
    setFilters((prev) => {
      const newState = { ...prev };
      // Use METRICS_CONFIG keys which match FilterConfig
      Object.keys(METRICS_CONFIG).forEach((key) => {
        // First check if the key exists in metricRanges using a type guard
        if (key in metricRanges) {
          // Now TypeScript knows this is a valid key for metricRanges
          const typedKey = key as keyof MetricRanges;
          // Create a new filter range with the properly typed key
          const filterRange = createFilterRange(asMetricKey(key), metricRanges[typedKey], prev);
          // Assign to newState with the same typed key
          newState[asMetricKey(key)] = filterRange;
        }
      });

      // Return a new object to ensure React detects the change
      return { ...newState };
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
    const resetState = createInitialFilterState(metricRanges, METRICS_CONFIG);
    const resetInputValues: Record<string, { min: string; max: string }> = {};

    // Reset input values state
    Object.keys(resetState).forEach((key) => {
      const metricKey = asMetricKey(key);
      if (resetState[metricKey]) {
        resetInputValues[metricKey] = {
          min: Number(resetState[metricKey].current[0]).toFixed(3),
          max: Number(resetState[metricKey].current[1]).toFixed(3),
        };
      }
    });

    // Update both states
    setFilters(resetState);
    setInputValues(resetInputValues);
    setSelectedOption('AND');

    // Also apply the reset filters to update the scatter plot
    if (onApplyFilters) {
      onApplyFilters(createEmptyFilterConfig(), 'AND');
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

  const handleInputChange =
    (key: keyof FilterState, isMin: boolean) => (event: React.ChangeEvent<HTMLInputElement>) => {
      const inputValue = event.target.value;

      // Update the input value state
      updateInputValues(key, isMin, inputValue);

      // If empty, allow the field to be empty but don't update filter state
      if (inputValue === '' || isNaN(Number(inputValue))) {
        return;
      }

      // Apply 3 decimal precision
      const formattedValue = Number(Number(inputValue).toFixed(3));

      // Update filters state with a new object reference to ensure React detects the change
      setFilters((prev) => {
        const currentMax = isMin ? (prev[key]?.current[1] ?? 0) : Math.max(formattedValue, prev[key]?.current[0] ?? 0);
        const currentMin = isMin ? Math.min(formattedValue, prev[key]?.current[1] ?? 0) : (prev[key]?.current[0] ?? 0);

        return {
          ...prev,
          [key]: {
            ...prev[key],
            current: [currentMin, currentMax],
          },
        };
      });
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
                  const metricKey = asMetricKey(key);
                  acc[metricKey] = [...value.current];
                }
                return acc;
              },
              {} as Required<FilterConfig>['filters']
            )
          : {},
        filter_type: option,
      };

      // Create a new object reference to ensure React detects the change
      onApplyFilters({ ...filterConfig }, option);
    }
  };

  const handleUncheckAll = () => {
    setFilters((prev) => {
      const newState = { ...prev };
      Object.keys(newState).forEach((key) => {
        const metricKey = asMetricKey(key);
        newState[metricKey] = {
          ...newState[metricKey],
          enabled: false,
        } as MetadataFilterRange;
      });
      return { ...newState };
    });
  };

  return (
    <Paper className={styles.filterPaper} elevation={1}>
      <FilterHeader selectedOption={selectedOption} onOptionChange={(option) => setSelectedOption(option)} />

      {Object.keys(filters).map((key) => (
        <FilterItem
          key={`filter-${key}`}
          metricKey={asMetricKey(key)}
          filter={filters[asMetricKey(key)]!}
          config={METRICS_CONFIG[asMetricKey(key)]}
          inputValues={inputValues[asMetricKey(key)]}
          summaryAPIData={summaryAPIData}
          onSliderChange={handleSliderChange(asMetricKey(key))}
          onCheckboxChange={handleCheckboxChange(asMetricKey(key))}
          onInputChange={handleInputChange}
          onInputBlur={handleInputBlur}
        />
      ))}

      <FilterControls
        onReset={handleReset}
        onUncheckAll={handleUncheckAll}
        onApplyFilters={() => handleApplyFilters(filters, selectedOption)}
      />
    </Paper>
  );
};
