import React, { useEffect, useRef, useMemo } from 'react';
import * as echarts from 'echarts';
import { MetadataVizResponse } from '../../../common/types/metadataViz/metadataVizData';
import styles from '../MetadataViz.module.css';
import {
  createTooltipFormatter,
  getPositionsMapping,
  createGridConfig,
  createXAxisConfig,
  createYAxisConfig,
  createSeriesConfig,
} from '../utils/ScatterPlotUtils';

interface MetricScatterPlotProps {
  data: MetadataVizResponse;
  processedData: ProcessedData;
  isLoading?: boolean;
  error?: boolean | { status: number; message: string };
  isFilterApplied: boolean;
  hoveredPosition?: string | null;
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

export const MetricScatterPlot: React.FC<MetricScatterPlotProps> = ({ 
  data, 
  processedData, 
  isFilterApplied,
  hoveredPosition 
}) => {
  const chartRef = useRef<HTMLDivElement>(null);
  const chartInstance = useRef<echarts.ECharts>();

  // Memoize position mapping to avoid recalculation
  const positionsMapping = useMemo(
    () => getPositionsMapping(data.accepted_results, data.rejected_results),
    [data.accepted_results, data.rejected_results]
  );

  // Memoize metrics configuration
  const metricsConfig = useMemo(
    () =>
      processedData.metricsConfig.map((metric) => ({
        key: metric.key,
        label: metric.label,
        unit: metric.unit,
      })),
    [processedData.metricsConfig]
  );

  // Memoize chart options to prevent unnecessary recalculations
  const chartOptions = useMemo(() => {
    if (!data?.accepted_results) return null;

    return {
      tooltip: {
        trigger: 'item' as const,
        formatter: createTooltipFormatter(data, processedData, isFilterApplied),
        backgroundColor: 'rgba(255, 255, 255, 0.95)',
        borderColor: '#ccc',
        borderWidth: 1,
        padding: [10, 15],
        textStyle: {
          color: '#333',
          fontSize: 13,
        },
      },
      grid: createGridConfig(metricsConfig.length),
      xAxis: createXAxisConfig(metricsConfig, positionsMapping.maxPositionIndex),
      yAxis: createYAxisConfig(metricsConfig, data),
      series: createSeriesConfig(metricsConfig, data, isFilterApplied, positionsMapping, hoveredPosition),
    };
  }, [data, processedData, metricsConfig, isFilterApplied, positionsMapping, hoveredPosition]);

  // Initialize and update chart
  useEffect(() => {
    if (!chartRef.current || !chartOptions) return;

    // Calculate total height based on number of metrics
    const gridHeight = 140;
    const spacing = 35;
    const totalHeight = processedData.metricsConfig.length * (gridHeight + spacing);
    chartRef.current.style.height = `${totalHeight}px`;

    // Force chart recreation when isFilterApplied changes or when options change significantly
    if (chartInstance.current) {
      chartInstance.current.dispose();
    }

    // Create new chart instance
    chartInstance.current = echarts.init(chartRef.current);
    chartInstance.current.setOption(chartOptions);
    chartInstance.current.resize();

    return () => {
      // Cleanup function to dispose chart when component unmounts or options change
      if (chartInstance.current) {
        chartInstance.current.dispose();
      }
    };
  }, [chartOptions, processedData.metricsConfig.length]);

  // Handle window resize
  useEffect(() => {
    const handleResize = () => {
      if (chartInstance.current) {
        chartInstance.current.resize();
      }
    };

    window.addEventListener('resize', handleResize);
    return () => {
      window.removeEventListener('resize', handleResize);
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