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
        // axisPointer: {
        //   type: 'cross',
        //   label: {
        //     backgroundColor: '#6a7985'
        //   }
        // },
        // position: function (point, params, dom, rect, size) {
        //   // Position the tooltip near the data point
        //   return [point[0] + 10, point[1] - 10];
        // }
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


  // Update chart when hoveredPosition changes
  useEffect(() => {
    if (chartInstance.current && hoveredPosition !== undefined) {
      if (hoveredPosition) {
        const posIndex = positionsMapping.positionMap.get(hoveredPosition) || -1;
        if (posIndex >= 0) {
          // First highlight the point
          chartInstance.current.dispatchAction({
            type: 'highlight',
            seriesIndex: 0, // Just highlight the first series for simplicity
            dataIndex: posIndex
          });
          
          // Then show the tooltip
          chartInstance.current.dispatchAction({
            type: 'showTip',
            seriesIndex: 0, // Just show tooltip for the first series
            dataIndex: posIndex
          });
        }
      } else {
        // Hide tooltip and remove highlights when not hovering
        chartInstance.current.dispatchAction({
          type: 'downplay',
          seriesIndex: 'all'
        });
        
        chartInstance.current.dispatchAction({
          type: 'hideTip'
        });
      }
    }
  }, [hoveredPosition, positionsMapping.positionMap]);
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

  // Update chart when hoveredPosition changes
  useEffect(() => {
    if (chartInstance.current && hoveredPosition !== undefined) {
      // Highlight the specific position or reset highlights
      chartInstance.current.dispatchAction({
        type: hoveredPosition ? 'highlight' : 'downplay',
        seriesIndex: 'all',
        dataIndex: hoveredPosition 
          ? Array.from({ length: metricsConfig.length }).map((_, i) => {
              // Find the position index that matches the hovered position name
              const posIndex = positionsMapping.positionMap.get(hoveredPosition) || -1;
              return posIndex;
            })
          : undefined
      });
      
      // Show tooltip for the hovered position
      if (hoveredPosition) {
        const posIndex = positionsMapping.positionMap.get(hoveredPosition) || -1;
        if (posIndex >= 0) {
          // Find the correct series and data point for the tooltip
          // We need to show tooltip for all metrics that have this position
          metricsConfig.forEach((_, metricIndex) => {
            chartInstance.current.dispatchAction({
              type: 'showTip',
              seriesIndex: isFilterApplied ? metricIndex * 2 : metricIndex, // For filtered view, each metric has 2 series
              dataIndex: posIndex
            });
          });
        }
      } else {
        chartInstance.current.dispatchAction({
          type: 'hideTip'
        });
      }
    }
  }, [hoveredPosition, metricsConfig.length, positionsMapping.positionMap]);

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