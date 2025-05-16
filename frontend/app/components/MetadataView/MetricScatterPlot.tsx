import React, { useEffect, useRef, useCallback } from 'react';
import * as echarts from 'echarts';
import { MetadataVizResponse, Metrics } from '../../common/types/metadataViz/metadataVizData';
import styles from './MetadataViz.module.css';
import { SCATTERPLOT_METRIC_COLORS } from './constants/MetricConfig';


interface MetricScatterPlotProps {
  data: MetadataVizResponse;
  processedData: ProcessedData;
  isLoading?: boolean;
  error?: boolean | { status: number; message: string };
  isFilterApplied: boolean;
}

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

// Helper to format metric key to label
const formatMetricLabel = (key: string): string => {
  return key
    .split('_')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
};

console.log('formatMetricLabel', formatMetricLabel);
// Sturges' formula for calculating number of bins
const calculateBins = (values: number[] | any): number => {
  // Ensure values is an array and filter out any non-numeric values
  if (!Array.isArray(values)) {
    return 5; // Default number of bins if values is not an array
  }
  
  // Filter out any non-numeric values
  const numericValues = values.filter(v => typeof v === 'number' && !isNaN(v));
  const n = numericValues.length;
  
  if (n <= 1) return 1;
  
  // Get the actual min and max from the filtered data
  const min = Math.min(...numericValues);
  const max = Math.max(...numericValues);
  const range = max - min;
  
  // Use Freedman-Diaconis rule which is more robust to outliers
  // and considers the distribution of the data
  const iqr = calculateIQR(numericValues);
  if (iqr === 0) {
    // Fall back to Sturges' formula if IQR is zero
    return Math.ceil(1 + 3.322 * Math.log10(n));
  }
  
  const binWidth = 2 * iqr / Math.pow(n, 1/3);
  return Math.max(1, Math.ceil(range / binWidth));
};

// Helper function to calculate Interquartile Range
const calculateIQR = (values: number[]): number => {
  if (!values.length) return 0;
  
  const sorted = [...values].sort((a, b) => a - b);
  const q1 = sorted[Math.floor(sorted.length * 0.25)];
  const q3 = sorted[Math.floor(sorted.length * 0.75)];
  return q3 - q1;
};


export const MetricScatterPlot: React.FC<MetricScatterPlotProps> = ({ data, processedData, isFilterApplied }) => {
  const chartRef = useRef<HTMLDivElement>(null);
  const chartInstance = useRef<echarts.ECharts>();

  // Create tooltip formatter function
  const createTooltipFormatter = useCallback(() => {
    return function (params: echarts.TooltipComponentFormatterCallbackParams) {
      const param = Array.isArray(params) ? params[0] : params;
      const dataIndex = param.dataIndex as number;
      
      // Check if dataIndex is valid and accepted_results exists
      if (dataIndex === undefined || !data?.accepted_results || dataIndex >= data.accepted_results.length) {
        return 'No data available';
      }
      
      const tiltSeries = data.accepted_results[dataIndex];
      
      // Check if tiltSeries exists
      if (!tiltSeries) {
        return 'No data available';
      }
      
      const metrics = tiltSeries.metrics;
      
      // Check if metrics exists
      if (!metrics) {
        return 'No metrics data available';
      }

      let tooltipContent = `<div style="font-weight: bold; margin-bottom: 5px;">Position : ${tiltSeries.name || 'Unknown'}</div>`;

      // Helper function to format the metric line with safety checks
      const formatMetricLine = (key: keyof Metrics, label: string, unit: string, multiplier = 1) => {
        if (metrics[key] === undefined || metrics[key] === null) {
          return `<div>${label}: N/A ${unit}</div>`;
        }
        const value = metrics[key] * multiplier;
        return `<div>${label}: ${value.toFixed(2)} ${unit}</div>`;
      };

      // Add all metric values to tooltip with safety checks
      if (processedData?.metricsConfig) {
        tooltipContent += processedData.metricsConfig
          .map(({ key, label, unit }) => {
            const multiplier = key.includes('bad_patch') ? 100 : 1;
            return formatMetricLine(key as keyof Metrics, label, unit, multiplier);
          })
          .join('');
      }

      return tooltipContent;
    };
  }, [data, processedData, isFilterApplied]);
// Create grid configuration
const createGridConfig = useCallback((metricsConfig: Array<{ key: string; label: string }>) => {
  const gridHeight = 140; 
  const spacing = 38; 
  
  return metricsConfig.map((_, index) => ({
    containLabel: true,
    top: index * (gridHeight + spacing),
    height: gridHeight,
    left: '5%',
    right: '9%',
    show: true,
  }));
}, []);

  // Create X-axis configuration
  const createXAxisConfig = useCallback(
    (metricsConfig: Array<{ key: string; label: string }>) => {
      const hasRejectedResults = data.rejected_results && data.rejected_results.length > 0;
      const totalPoints = hasRejectedResults 
        ? Math.max(data.accepted_results.length, data.rejected_results.length) - 1
        : data.accepted_results.length - 1;

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
        max: totalPoints,
        splitLine: {
          show: false,
        },
      }));
    },
    [data]
  );

 // Create Y-axis configuration
const createYAxisConfig = useCallback(() => {
  return processedData?.metricsConfig.map((metric, index) => {
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
      name: `${metric.label} \n${metric.unit}`,
      nameLocation: 'middle' as const,
      nameGap: 60, 
      nameTextStyle: {
        fontSize: 15,
        fontWeight: 'bold' as const,
        align: 'center' as const,
      },
      splitNumber: calculateBins(values.length),
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
}, [data, processedData]);
const createSeriesConfig = useCallback(
  (metricsConfig: Array<{ key: string; label: string }>) => {
    // Check if we're in a filtered state or default state
    // Only use filtered view if:
    // 1. isFilterApplied is true (explicit filter was applied)
    // 2. rejected_results exists and has items
    const hasRejectedResults = data.rejected_results && data.rejected_results.length > 0;
    // Force all metrics to use the same visualization mode - either all filtered or all default
    const shouldUseFilteredView = isFilterApplied && hasRejectedResults;
    
    console.log('Scatter plot visualization mode:', { isFilterApplied, hasRejectedResults, shouldUseFilteredView });
    
    const maxLength = Math.max(data.accepted_results.length, data.rejected_results?.length || 0);
    
    // Pre-calculate normalized positions
    const normalizedAcceptedPositions = data.accepted_results.map((_, pos) => 
      pos * (data.accepted_results.length / maxLength)
    );
    const normalizedRejectedPositions = data.rejected_results?.map((_, pos) => 
      pos * (data.rejected_results!.length / maxLength)
    ) || [];

    // Force consistent visualization mode for ALL metrics
    return metricsConfig.map((metric, index) => {
      if (!shouldUseFilteredView) {
        // Default view with metric-specific colors
        return {
          type: 'scatter' as const,
          name: metric.label,
          xAxisIndex: index,
          yAxisIndex: index,
          symbolSize: 4,
          itemStyle: {
            opacity: 0.6,
            color: SCATTERPLOT_METRIC_COLORS[metric.key as keyof typeof SCATTERPLOT_METRIC_COLORS],
          },
          data: data.accepted_results.map((item, pos) => {
            if (!item?.metrics) return [normalizedAcceptedPositions[pos], 0];
            const value = item.metrics[metric.key as keyof Metrics];
            return [normalizedAcceptedPositions[pos], metric.key.includes('bad_patch') ? value * 100 : value];
          }),
        };
      } else {
        // Filtered view with accepted (green) and rejected (red) points
        return [
          {
            type: 'scatter' as const,
            name: `${metric.label} (Accepted)`,
            xAxisIndex: index,
            yAxisIndex: index,
            symbolSize: 4,
            itemStyle: {
              opacity: 0.6,
              color: '#4CAF50',
            },
            data: data.accepted_results.map((item, pos) => {
              if (!item?.metrics) return [normalizedAcceptedPositions[pos], 0];
              const value = item.metrics[metric.key as keyof Metrics];
              return [normalizedAcceptedPositions[pos], metric.key.includes('bad_patch') ? value * 100 : value];
            }),
          },
          {
            type: 'scatter' as const,
            name: `${metric.label} (Rejected)`,
            xAxisIndex: index,
            yAxisIndex: index,
            symbolSize: 4,
            itemStyle: {
              opacity: 0.6,
              color: '#F44336',
            },
            data: data.rejected_results.map((item, pos) => {
                if (!item?.metrics) return [normalizedRejectedPositions[pos], 0];
                const value = item.metrics[metric.key as keyof Metrics];
                return [normalizedRejectedPositions[pos], metric.key.includes('bad_patch') ? value * 100 : value];
            }),
          },
        ];
      }
    }).flat();
  },
  [data, processedData, isFilterApplied]
);

  useEffect(() => {
    if (!chartRef.current || !data?.accepted_results) return;

    // Calculate total height based on number of metrics
    const gridHeight = 140;
    const spacing = 35;
    const totalHeight = processedData.metricsConfig.length * (gridHeight + spacing);
    chartRef.current.style.height = `${totalHeight}px`;
    
    // Force chart recreation when isFilterApplied changes
    if (chartInstance.current) {
      chartInstance.current.dispose();
      chartInstance.current = undefined;
    }

    if (!chartInstance.current) {
      chartInstance.current = echarts.init(chartRef.current);
    }

    // Generate metrics config from the data
    const metricsConfig = processedData.metricsConfig.map((metric) => ({
      key: metric.key,
      label: metric.label,
    }));

    const option: echarts.EChartsOption = {
      tooltip: {
        trigger: 'item',
        formatter: createTooltipFormatter(),
        backgroundColor: 'rgba(255, 255, 255, 0.95)',
        borderColor: '#ccc',
        borderWidth: 1,
        padding: [10, 15],
        textStyle: {
          color: '#333',
          fontSize: 13,
        },
      },
      grid: createGridConfig(metricsConfig),
      xAxis: createXAxisConfig(metricsConfig),
      yAxis: createYAxisConfig(),
      series: createSeriesConfig(metricsConfig),
    };

    chartInstance.current.setOption(option);
    chartInstance.current.resize();
  }, [
    data,
    processedData,
    createGridConfig,
    createTooltipFormatter,
    createXAxisConfig,
    createYAxisConfig,
    createSeriesConfig,
  ]);

  useEffect(() => {
    const handleResize = () => {
      if (chartInstance.current) {
        chartInstance.current.resize();
      }
    };

    window.addEventListener('resize', handleResize);
    return () => {
      window.removeEventListener('resize', handleResize);
      if (chartInstance.current) {
        chartInstance.current.dispose();
        chartInstance.current = undefined;
      }
    };
  }, []);

  return (
    <div className={styles.scatterPlotContainer}>
      {data ? (
        <div className={styles.plotContainer} ref={chartRef} />
      ) : (
        <div className={styles.noDataMessage}>{'No data available'}</div>
      )}
    </div>
  );
};
