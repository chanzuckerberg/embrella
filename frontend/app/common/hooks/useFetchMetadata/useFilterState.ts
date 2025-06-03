import { useState, useEffect, useMemo, useCallback } from 'react';
import { FilterConfig, MetricRanges } from '@app/common/types/metadataViz/metadataVizData';
import { FilterState, MetadataFilterRange } from '@app/common/types/metadataViz/FilterType';
import {
  createInitialFilterState,
  createFilterRange,
  createEmptyFilterConfig,
  asMetricKey,
} from '@app/components/MetadataView/utils/FilterUtils';
import { MetadataSummaryResponse } from '@app/common/types/metadataViz/metadataSummary';

interface UseFilterStateProps {
  metricRanges: MetricRanges;
  metricsConfig: Record<string, any>;
  initialFilterType?: 'AND' | 'OR';
  onApplyFilters?: (filters: FilterConfig, selectedOption: 'AND' | 'OR') => void;
  onFilterStateChange?: (isFilterApplied: boolean, filterConfig?: FilterConfig) => void;
  summaryAPIData?: MetadataSummaryResponse;
}

// Interface for median values
interface MedianValues {
  [key: string]: {
    value: number | undefined;
    hasMedian: boolean;
  };
}

export interface UseFilterStateReturn {
  // Filter state
  filters: FilterState;
  filterType: 'AND' | 'OR';
  inputValues: Record<string, { min: string; max: string }>;
  filterConfig: FilterConfig | undefined;
  medianValues: MedianValues;

  // Filter actions
  setFilterType: (type: 'AND' | 'OR') => void;
  setFilters: React.Dispatch<React.SetStateAction<FilterState>>;
  handleSliderChange: (key: keyof FilterState) => (event: Event, newValue: number | number[]) => void;
  handleCheckboxChange: (key: keyof FilterState) => (event: React.ChangeEvent<HTMLInputElement>) => void;
  handleInputChange: (key: keyof FilterState, isMin: boolean) => (event: React.ChangeEvent<HTMLInputElement>) => void;
  handleInputBlur: (key: keyof FilterState, isMin: boolean) => () => void;
  handleReset: () => void;
  handleApplyFilters: () => void;
  handleUncheckAll: () => void;
}

/**
 * Custom hook for managing filter state in metadata visualization components
 */
export const useFilterState = ({
  metricRanges,
  metricsConfig,
  initialFilterType = 'AND',
  onApplyFilters,
  onFilterStateChange,
  summaryAPIData,
}: UseFilterStateProps): UseFilterStateReturn => {
  // State for filter management
  const [filterType, setFilterType] = useState<'AND' | 'OR'>(initialFilterType);
  const [filters, setFilters] = useState<FilterState>(() => createInitialFilterState(metricRanges, metricsConfig));
  const [filterConfig, setFilterConfig] = useState<FilterConfig | undefined>();
  const [inputValues, setInputValues] = useState<Record<string, { min: string; max: string }>>({});

  // Calculate median values from summary data
  const medianValues = useMemo(() => {
    const result: MedianValues = {};

    // Initialize all keys with default values
    Object.keys(filters).forEach((key) => {
      const metricKey = asMetricKey(key);
      result[metricKey] = {
        value: undefined,
        hasMedian: false,
      };
    });

    // Only certain metrics have median values
    const medianMetrics = ['tilt_axis', 'global_shift'];

    if (summaryAPIData?.computed_metrics) {
      medianMetrics.forEach((metricKey) => {
        if (metricKey in result) {
          // Map metric keys to API response names
          const metricName = metricKey === 'tilt_axis' ? 'Tilt Axis' : 'Global Shift';

          // Find the metric in the array
          const metric = summaryAPIData.computed_metrics.find((m) => m.name.includes(metricName));

          if (metric?.median !== undefined) {
            result[metricKey] = {
              value: metric.median,
              hasMedian: true,
            };
          }
        }
      });
    }

    return result;
  }, [filters, summaryAPIData]);

  // Update filters when metric ranges change
  useEffect(() => {
    setFilters((prev) => {
      const newState = { ...prev };
      // Use metricsConfig keys which match FilterConfig
      Object.keys(metricsConfig).forEach((key) => {
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
  }, [metricRanges, metricsConfig]);

  // Helper function to update input values state
  const updateInputValues = useCallback(
    (key: keyof FilterState, isMin: boolean, value: string) => {
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
    },
    [filters]
  );

  // Handle slider change
  const handleSliderChange = useCallback(
    (key: keyof FilterState) => (_: Event, newValue: number | number[]) => {
      if (!Array.isArray(newValue)) return;

      setFilters((prev) => ({
        ...prev,
        [key]: {
          ...prev[key],
          current: [Math.max(newValue[0], prev[key]?.min ?? 0), Math.min(newValue[1], prev[key]?.max ?? 100)],
        },
      }));

      // Also update input values to reflect slider changes
      const minValue = Number(Math.max(newValue[0], filters[key]?.min ?? 0).toFixed(3));
      const maxValue = Number(Math.min(newValue[1], filters[key]?.max ?? 100).toFixed(3));
      
      setInputValues((prev) => ({
        ...prev,
        [key]: {
          min: minValue.toFixed(3),
          max: maxValue.toFixed(3),
        },
      }));
    },
    [filters]
  );


  // Handle checkbox change
  const handleCheckboxChange = useCallback(
    (key: keyof FilterState) => (event: React.ChangeEvent<HTMLInputElement>) => {
      setFilters((prev) => ({
        ...prev,
        [key]: {
          ...prev[key],
          enabled: event.target.checked,
        },
      }));
    },
    []
  );

  // Handle input change
  const handleInputChange = useCallback(
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
    },
    [updateInputValues]
  );

  // Handle input blur
  const handleInputBlur = useCallback(
    (key: keyof FilterState, isMin: boolean) => () => {
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
    },
    [filters]
  );

  // Handle reset
  const handleReset = useCallback(() => {
    const resetState = createInitialFilterState(metricRanges, metricsConfig);
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
    setFilterType('AND');

    // Create empty filter config
    const emptyConfig = createEmptyFilterConfig();
    setFilterConfig(emptyConfig);

    // Also apply the reset filters to update the scatter plot
    if (onApplyFilters) {
      onApplyFilters(emptyConfig, 'AND');
    }

    // Notify parent about filter state change if callback provided
    if (onFilterStateChange) {
      onFilterStateChange(false);
    }
  }, [metricRanges, metricsConfig, onApplyFilters, onFilterStateChange]);

  // Handle apply filters
  const handleApplyFilters = useCallback(() => {
    // Check if any filters are enabled
    const hasEnabledFilters = Object.values(filters).some((value) => value.enabled);

    const newFilterConfig: FilterConfig = {
      filters: hasEnabledFilters
        ? Object.entries(filters).reduce(
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
      filter_type: filterType,
    };

    // Create a new object reference to ensure React detects the change
    const finalConfig = { ...newFilterConfig };
    setFilterConfig(finalConfig);

    // Call the onApplyFilters callback if provided
    if (onApplyFilters) {
      onApplyFilters(finalConfig, filterType);
    }

    // Notify parent about filter state change if callback provided
    if (onFilterStateChange) {
      const isFilterApplied = hasEnabledFilters && Object.keys(newFilterConfig.filters).length > 0;
      onFilterStateChange(isFilterApplied, isFilterApplied ? finalConfig : undefined);
    }
  }, [filters, filterType, onApplyFilters, onFilterStateChange]);

  // Handle uncheck all
  const handleUncheckAll = useCallback(() => {
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
  }, []);

  return {
    // Filter state
    filters,
    filterType,
    inputValues,
    filterConfig,
    medianValues,

    // Filter actions
    setFilterType,
    setFilters,
    handleSliderChange,
    handleCheckboxChange,
    handleInputChange,
    handleInputBlur,
    handleReset,
    handleApplyFilters,
    handleUncheckAll,
  };
};
