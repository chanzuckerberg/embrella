import { FilterConfig, MetricRanges } from '@app/common/types/metadataViz/metadataVizData';
import { FilterState, MetadataFilterRange } from '@app/common/types/metadataViz/FilterType';
import { MetricConfigItem } from '../constants/MetricConfig';


export const asMetricKey = <T extends string>(key: string): keyof MetricRanges & keyof FilterState => {
    return key as keyof MetricRanges & keyof FilterState;
  };

/**
 * Creates the initial filter state from metric ranges and metrics config
 */
export const createInitialFilterState = (
  metricRanges: MetricRanges,
  metricsConfig: Record<string, MetricConfigItem>
): FilterState => {
  const initialState: FilterState = {} as FilterState;

  Object.keys(metricsConfig).forEach((key) => {
    const metricKey = key as keyof typeof metricsConfig;
    if (
      metricRanges[asMetricKey(metricKey)] &&
      Array.isArray(metricRanges[asMetricKey(metricKey)])
    ) {
      initialState[metricKey as keyof FilterState] = {
        current: [
          Number(metricRanges[asMetricKey(metricKey)][0]),
          Number(metricRanges[asMetricKey(metricKey)][1]),
        ],
        min: Number(metricRanges[asMetricKey(metricKey)][0]),
        max: Number(metricRanges[asMetricKey(metricKey)][1]),
        enabled: true,
      };
    }
  });

  return initialState;
};

/**
 * Creates a filter range object for a specific metric
 * Always returns a new object to ensure React detects state changes
 */
export const createFilterRange = (
  metricKey: string,
  range: [number, number] | undefined,
  prevState: FilterState
): MetadataFilterRange => {
  const currentRange: [number, number] = Array.isArray(range)
    ? [Number(range[0]), Number(range[1])]
    : prevState[asMetricKey(metricKey)]?.current || [0, 100];

  return {
    ...prevState[asMetricKey(metricKey)],
    current: [...currentRange], // Create a new array to ensure React detects the change
    min: Number(Array.isArray(range) ? range[0] : prevState[asMetricKey(metricKey)]?.min || 0),
    max: Number(Array.isArray(range) ? range[1] : prevState[asMetricKey(metricKey)]?.max || 100),
    enabled: prevState[asMetricKey(metricKey)]?.enabled ?? true,
  };
};

/**
 * Creates an empty filter config for resetting filters
 */
export const createEmptyFilterConfig = (): FilterConfig => ({
  filters: {},
  filter_type: 'AND',
});

/**
 * Determines the step value for a slider based on the metric key and range
 */
export const getStepValue = (key: string, minValue: number, maxValue: number): number => {
  return key === asMetricKey('bad_patch_low') || key === asMetricKey('bad_patch_all') ? 0.1 : (maxValue - minValue) / 100;
};
    