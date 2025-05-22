import React, { useEffect, useRef, useCallback } from 'react';
import * as echarts from 'echarts';
import { MetadataVizResponse, Metrics, TiltSeries } from '../../common/types/metadataViz/metadataVizData';
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

// Sturges' formula for calculating number of bins
const calculateBins = (values: number[] | undefined): number => {
  // Ensure values is an array and filter out any non-numeric values
  if (!Array.isArray(values)) {
    return 5; // Default number of bins if values is not an array
  }

  // // Filter out any non-numeric values
  // const numericValues = values.filter((v) => typeof v === 'number' && !isNaN(v));
  // const n = numericValues.length;

  // if (n <= 1) return 1;

  // // Get the actual min and max from the filtered data
  // const min = Math.min(...numericValues);
  // const max = Math.max(...numericValues);
  // const range = max - min;

  // // Use Freedman-Diaconis rule which is more robust to outliers
  // // and considers the distribution of the data
  // const iqr = calculateIQR(numericValues);
  // if (iqr === 0) {
  //   // Fall back to Sturges' formula if IQR is zero
  //   return Math.ceil(1 + 3.322 * Math.log10(n));
  // }

  // const binWidth = (2 * iqr) / Math.pow(n, 1 / 3);
  // return Math.max(1, Math.ceil(range / binWidth));
  return 5; // Simplified for now
};

export const MetricScatterPlot: React.FC<MetricScatterPlotProps> = ({ data, processedData, isFilterApplied }) => {
  const chartRef = useRef<HTMLDivElement>(null);
  const chartInstance = useRef<echarts.ECharts>();

  // Helper function to format the metric line with safety checks
  const formatMetricLine = (metrics: Metrics, key: keyof Metrics, label: string, unit: string, multiplier = 1) => {
    if (metrics[key] === undefined || metrics[key] === null) {
      return `<div>${label}: N/A ${unit}</div>`;
    }
    const value = metrics[key] * multiplier;
    return `<div>${label}: ${value.toFixed(2)} ${unit}</div>`;
  };
  // Extract tooltip data helper
  const extractTooltipData = useCallback(
    (params: echarts.TooltipComponentFormatterCallbackParams) => {
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
    },
    [data, isFilterApplied]
  );

  // Format tooltip content
  const formatTooltipContent = useCallback(
    (tiltSeries: { name?: string }, metricsData: Metrics) => {
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
    },
    [processedData]
  );

  // Create tooltip formatter function
  const createTooltipFormatter = useCallback(() => {
    // Main formatter function
    return (params: echarts.TooltipComponentFormatterCallbackParams) => {
      const data = extractTooltipData(params);
      return data ? formatTooltipContent(data.tiltSeries, data.metricsData) : 'No data available';
    };
  }, [extractTooltipData, formatTooltipContent]);

  // Helper to create positions with consistent mapping
  const getPositions = useCallback(() => {
    // Create a mapping of position names to their original indices
    const positionMap = new Map<string, number>();

    // First collect all unique position names from both accepted and rejected results
    const allPositions = new Set<string>();

    // Add all position names from accepted results
    data.accepted_results.forEach((item) => {
      if (item.name) {
        allPositions.add(item.name);
      }
    });

    // Add all position names from rejected results
    if (data.rejected_results) {
      data.rejected_results.forEach((item) => {
        if (item.name) {
          allPositions.add(item.name);
        }
      });
    }

    // Create a consistent mapping for all positions
    // Sort the names to ensure consistent ordering
    Array.from(allPositions)
      .sort()
      .forEach((name, index) => {
        positionMap.set(name, index);
      });

    // Get all unique position indices for complete visualization
    const allPositionIndices = Array.from(allPositions).map((name) => positionMap.get(name) || 0);

    // Now use the position map to get consistent indices
    return {
      positionMap,
      acceptedPositions: data.accepted_results.map((item) => (item.name ? positionMap.get(item.name) || 0 : 0)),
      rejectedPositions: data.rejected_results?.map((item) => (item.name ? positionMap.get(item.name) || 0 : 0)) || [],
      allPositionIndices,
      maxPositionIndex: allPositionIndices.length > 0 ? Math.max(...allPositionIndices) + 1 : 0,
    };
  }, [data]);

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
      // Use the maximum position index from all unique positions
      const { maxPositionIndex } = getPositions();

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
    },
    [getPositions]
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
  }, [data, processedData]);

  const createSeriesConfig = useCallback(
    (metricsConfig: Array<{ key: string; label: string }>) => {
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
      const createDefaultSeries = (metric: { key: string; label: string }, index: number, positions: number[]) => {
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
        metric: { key: string; label: string },
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

      const { positionMap, acceptedPositions, allPositionIndices } = getPositions();

      // Create series based on visualization mode
      return metricsConfig
        .map((metric, index) => {
          if (!shouldUseFilteredView) {
            return createDefaultSeries(metric, index, acceptedPositions);
          } else {
            return createFilteredSeries(metric, index, positionMap, allPositionIndices);
          }
        })
        .flat();
    },
    [data, isFilterApplied, getPositions]
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
    isFilterApplied,
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
