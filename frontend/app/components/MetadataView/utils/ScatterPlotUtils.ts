import * as echarts from 'echarts';
import { MetadataVizResponse, Metrics, TiltSeries } from '../../../common/types/metadataViz/metadataVizData';
import { SCATTERPLOT_METRIC_COLORS } from '../constants/MetricConfig';

interface ProcessedData {
  metricsConfig: Array<{
    key: string;
    label: string;
    values: number[];
    range: [number, number];
    unit: string;
  }>;
  totalPositions: number;
}

interface MetricConfig {
  key: string;
  label: string;
  unit?: string;
}

interface PositionsMapping {
  positionMap: Map<string, number>;
  acceptedPositions: number[];
  rejectedPositions: number[];
  allPositionIndices: number[];
  maxPositionIndex: number;
}

// Sturges' formula for calculating number of bins
export const calculateBins = (values: number[] | undefined): number => {
  // Ensure values is an array and filter out any non-numeric values
  if (!Array.isArray(values)) {
    return 5; // Default number of bins if values is not an array
  }

  return 5; // Simplified for now
};

// Helper function to format the metric line with safety checks
export const formatMetricLine = (metrics: Metrics, key: keyof Metrics, label: string, unit: string, multiplier = 1) => {
  if (metrics[key] === undefined || metrics[key] === null) {
    return `<div>${label}: N/A ${unit}</div>`;
  }
  const value = metrics[key] * multiplier;
  return `<div>${label}: ${value.toFixed(2)} ${unit}</div>`;
};

// Extract tooltip data helper
export const extractTooltipData = (
  params: echarts.TooltipComponentFormatterCallbackParams,
  data: MetadataVizResponse,
  isFilterApplied: boolean
) => {
  const param = Array.isArray(params) ? params[0] : params;
  const dataIndex = param.dataIndex as number;
  const seriesName = param.seriesName || '';

  // Check if this is from a rejected series when filters are applied
  const isRejectedSeries = isFilterApplied && seriesName.includes('Rejected');

  // If it's a rejected series, look in rejected_results
  if (isRejectedSeries && data?.rejected_results) {
    // Basic validation for rejected data
    if (dataIndex === undefined || dataIndex >= data.rejected_results.length) {
      return null;
    }

    const tiltSeries = data.rejected_results[dataIndex];
    if (!tiltSeries || !tiltSeries.metrics) {
      return null;
    }

    return { tiltSeries, metricsData: tiltSeries.metrics };
  } else {
    // Original logic for accepted results
    if (dataIndex === undefined || !data?.accepted_results || dataIndex >= data.accepted_results.length) {
      return null;
    }

    const tiltSeries = data.accepted_results[dataIndex];
    if (!tiltSeries || !tiltSeries.metrics) {
      return null;
    }

    return { tiltSeries, metricsData: tiltSeries.metrics };
  }
};

// Format tooltip content
export const formatTooltipContent = (
  tiltSeries: { name?: string },
  metricsData: Metrics,
  processedData: ProcessedData
) => {
  let content = `<div style="font-weight: bold; margin-bottom: 5px;">Position : ${tiltSeries.name || 'Unknown'}</div>`;

  if (processedData?.metricsConfig) {
    content += processedData.metricsConfig
      .map(({ key, label, unit }) => {
        const multiplier = key.includes('bad_patch') ? 100 : 1;
        return formatMetricLine(metricsData, key as keyof Metrics, label, unit, multiplier);
      })
      .join('');
  }

  return content;
};

// Create tooltip formatter function
export const createTooltipFormatter = (
  data: MetadataVizResponse,
  processedData: ProcessedData,
  isFilterApplied: boolean
) => {
  // Main formatter function
  return (params: echarts.TooltipComponentFormatterCallbackParams) => {
    const tooltipData = extractTooltipData(params, data, isFilterApplied);
    return tooltipData
      ? formatTooltipContent(tooltipData.tiltSeries, tooltipData.metricsData, processedData)
      : 'No data available';
  };
};

// Helper to create positions with consistent mapping
export const getPositionsMapping = (
  acceptedResults: TiltSeries[],
  rejectedResults?: TiltSeries[]
): PositionsMapping => {
  // Collect all unique position names from both result sets
  const allPositions = new Set<string>(
    [...acceptedResults, ...(rejectedResults || [])].filter((item) => item.name).map((item) => item.name as string)
  );

  // Create a consistent mapping for all positions (sorted to ensure consistent ordering)
  const positionMap = new Map<string, number>();
  Array.from(allPositions)
    .sort()
    .forEach((name, index) => {
      positionMap.set(name, index);
    });

  // Get position indices for accepted and rejected results
  const acceptedPositions = acceptedResults.map((item) => (item.name ? positionMap.get(item.name) || 0 : 0));

  const rejectedPositions = rejectedResults
    ? rejectedResults.map((item) => (item.name ? positionMap.get(item.name) || 0 : 0))
    : [];

  // Get all unique position indices for complete visualization
  const allPositionIndices = Array.from(positionMap.values());
  const maxPositionIndex = allPositionIndices.length > 0 ? Math.max(...allPositionIndices) + 1 : 0;

  return {
    positionMap,
    acceptedPositions,
    rejectedPositions,
    allPositionIndices,
    maxPositionIndex,
  };
};

// Create grid configuration
export const createGridConfig = (metricCount: number) => {
  const gridHeight = 140;
  const spacing = 38;

  return Array(metricCount)
    .fill(0)
    .map((_, index) => ({
      containLabel: true,
      top: index * (gridHeight + spacing),
      height: gridHeight,
      left: '5%',
      right: '9%',
      show: true,
    }));
};

// Create X-axis configuration
export const createXAxisConfig = (metricsConfig: MetricConfig[], maxPositionIndex: number) => {
  return metricsConfig.map((_, index) => ({
    type: 'value' as const,
    gridIndex: index,
    name: 'Position',
    position: 'bottom' as const,
    axisLabel: {
      show: false,
    },
    axisLine: {
      show: false,
    },
    axisTick: {
      show: false,
    },
    nameGap: 40,
    nameTextStyle: {
      fontSize: 14,
      fontWeight: 'bold' as const,
      wrap: true,
    },
    min: 0,
    max: maxPositionIndex,
    splitLine: {
      show: false,
    },
  }));
};

// Create Y-axis configuration
export const createYAxisConfig = (metricsConfig: MetricConfig[], data: MetadataVizResponse) => {
  return metricsConfig.map((metric, index) => {
    const values = data.accepted_results.map((item) => {
      const value = item.metrics[metric.key as keyof Metrics];
      return metric.key.includes('bad_patch') ? value * 100 : value;
    });

    const [min, max] = metric.key.includes('bad_patch')
      ? [
          data.metric_ranges[metric.key as keyof Metrics][0] * 100,
          data.metric_ranges[metric.key as keyof Metrics][1] * 100,
        ]
      : data.metric_ranges[metric.key as keyof Metrics];
    const range = max - min;
    const padding = range * 0.05;

    return {
      type: 'value' as const,
      gridIndex: index,
      name: `${metric.label} \n${metric.unit || ''}`,
      nameLocation: 'middle' as const,
      nameGap: 60,
      nameTextStyle: {
        fontSize: 15,
        fontWeight: 'bold' as const,
        align: 'center' as const,
      },
      splitNumber: calculateBins(values),
      min: min - padding,
      max: max + padding,
      splitLine: {
        show: true,
        lineStyle: {
          type: 'dashed' as const,
          opacity: 0.3,
        },
      },
      axisTick: {
        show: false,
      },
      axisLine: {
        show: false,
      },
      axisLabel: {
        show: true,
        margin: 8,
        fontSize: 10,
        formatter: (value: number) => value.toFixed(2),
      },
    };
  });
};

// Create series configuration
export const createSeriesConfig = (
  metricsConfig: MetricConfig[],
  data: MetadataVizResponse,
  isFilterApplied: boolean,
  positionsMapping: PositionsMapping
) => {
  // Check if we're in a filtered state or default state
  const hasRejectedResults = data.rejected_results && data.rejected_results.length > 0;
  const shouldUseFilteredView = isFilterApplied && hasRejectedResults;

  // Helper to create data points for a series - modified to handle position mapping correctly
  const createDataPoints = (items: TiltSeries[], positions: number[], metricKey: string) => {
    return items.map((item, idx) => {
      if (!item?.metrics) return [positions[idx], 0];
      const value = item.metrics[metricKey as keyof Metrics];
      return [positions[idx], metricKey.includes('bad_patch') ? value * 100 : value];
    });
  };

  // Helper to create default series
  const createDefaultSeries = (metric: MetricConfig, index: number, positions: number[]) => {
    return {
      type: 'scatter' as const,
      name: metric.label,
      xAxisIndex: index,
      yAxisIndex: index,
      symbolSize: 5,
      itemStyle: {
        opacity: 0.6,
        color: SCATTERPLOT_METRIC_COLORS[metric.key as keyof typeof SCATTERPLOT_METRIC_COLORS],
      },
      data: createDataPoints(data.accepted_results, positions, metric.key),
    };
  };

  // Helper to create filtered series
  const createFilteredSeries = (
    metric: MetricConfig,
    index: number,
    positionMap: Map<string, number>,
    allPositionIndices: number[]
  ) => {
    // Create mappings to track which positions have accepted/rejected values
    const acceptedValuesByPosition = new Map<number, number>();
    const rejectedValuesByPosition = new Map<number, number>();

    // Map accepted values to their positions
    data.accepted_results.forEach((item) => {
      if (item.name && item.metrics) {
        const posIndex = positionMap.get(item.name) || 0;
        const value = item.metrics[metric.key as keyof Metrics];
        acceptedValuesByPosition.set(posIndex, metric.key.includes('bad_patch') ? value * 100 : value);
      }
    });

    // Map rejected values to their positions
    if (data.rejected_results) {
      data.rejected_results.forEach((item) => {
        if (item.name && item.metrics) {
          const posIndex = positionMap.get(item.name) || 0;
          const value = item.metrics[metric.key as keyof Metrics];
          rejectedValuesByPosition.set(posIndex, metric.key.includes('bad_patch') ? value * 100 : value);
        }
      });
    }

    // Create data arrays for accepted and rejected points
    const acceptedData: [number, number][] = [];
    const rejectedData: [number, number][] = [];

    // For each position index, add it to the appropriate array if it has a value
    allPositionIndices.forEach((posIndex) => {
      if (acceptedValuesByPosition.has(posIndex)) {
        acceptedData.push([posIndex, acceptedValuesByPosition.get(posIndex)!]);
      }

      if (rejectedValuesByPosition.has(posIndex)) {
        rejectedData.push([posIndex, rejectedValuesByPosition.get(posIndex)!]);
      }
    });

    return [
      {
        type: 'scatter' as const,
        name: `${metric.label} (Accepted)`,
        xAxisIndex: index,
        yAxisIndex: index,
        symbolSize: 5,
        itemStyle: {
          opacity: 0.6,
          color: '#006400',
        },
        data: acceptedData,
      },
      {
        type: 'scatter' as const,
        name: `${metric.label} (Rejected)`,
        xAxisIndex: index,
        yAxisIndex: index,
        symbolSize: 5,
        itemStyle: {
          opacity: 0.6,
          color: '#B00020',
        },
        data: rejectedData,
      },
    ];
  };

  // Create series based on visualization mode
  return metricsConfig
    .map((metric, index) => {
      if (!shouldUseFilteredView) {
        return createDefaultSeries(metric, index, positionsMapping.acceptedPositions);
      } else {
        return createFilteredSeries(metric, index, positionsMapping.positionMap, positionsMapping.allPositionIndices);
      }
    })
    .flat();
};
