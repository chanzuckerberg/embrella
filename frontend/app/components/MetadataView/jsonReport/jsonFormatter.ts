import { MetadataVizResponse } from '@app/common/types/metadataViz/metadataVizData';
import { METRICS_CONFIG } from '../constants/MetricConfig';

export interface FocusedJsonData {
  'Selected positions': string[];
  'Filtering ranges': Record<string, string>;
  'Filter type': string;
}

export const createFocusedJson = (
  data?: MetadataVizResponse,
  sortEnabled = false,
  sortBy = '',
  sortDirection: 'asc' | 'desc' = 'asc'
): FocusedJsonData => {
  if (!data) {
    return { 'Selected positions': [], 'Filtering ranges': {}, 'Filter type': 'None' };
  }

  // Get position names from accepted results
  let positionNames = data.accepted_results?.map((item) => item.name) || [];

  // Apply client-side sorting for position names if no metric is selected
  if (sortEnabled && sortBy === 'Select Metric' && positionNames.length > 0) {
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
