import React, { useEffect, useRef } from 'react';
import * as echarts from 'echarts';
import { MetadataVizResponse } from '../../../common/types/metadataViz/metadataVizData';
import styles from '../MetadataViz.module.css';
import { HISTOGRAM_METRIC_COLORS } from '../constants/MetricConfig';

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

interface MetricHistogramProps {
  data: MetadataVizResponse;
  processedData: ProcessedData;
}

// Sturges' formula for calculating number of bins
const calculateBins = (n: number): number => {
  return Math.ceil(1 + 3.322 * Math.log10(n));
};

export const MetricHistogram: React.FC<MetricHistogramProps> = ({ data, processedData }) => {
  const chartRef = useRef<HTMLDivElement>(null);
  const chartInstance = useRef<echarts.ECharts>();

  useEffect(() => {
    if (!chartRef.current || !data?.accepted_results?.length) return;

    if (!chartInstance.current) {
      chartInstance.current = echarts.init(chartRef.current);
    }

    const option: echarts.EChartsOption = {
      tooltip: {
        trigger: 'item',
        formatter: function (params: echarts.TooltipComponentFormatterCallbackParams) {
          // Ensure params is treated as a single item, not an array
          const param = Array.isArray(params) ? params[0] : params;

          // Determine which metric index we're dealing with
          const seriesIndex = param.seriesIndex !== undefined ? param.seriesIndex : 0;
          const metric = processedData.metricsConfig[seriesIndex];

          const binValue = parseFloat(param.name);
          const isBadPatch = metric.key.includes('bad_patch');

          // Calculate bin width and end value
          const binCount = calculateBins(metric.values.length);
          const binWidth = (metric.range[1] - metric.range[0]) / binCount;

          // Get the bin index for this bar
          const min = metric.range[0];
          const binIndex = Math.floor((binValue - min) / binWidth);

          // Find actual values that fall into this bin
          const valuesInBin = metric.values.filter((value) => {
            const valueBinIndex = Math.floor((value - min) / binWidth);
            return valueBinIndex === binIndex;
          });

          // Calculate actual min and max values in this bin (if any values exist)
          let actualMin = null;
          let actualMax = null;
          let rangeText = 'No data';

          if (valuesInBin.length > 0) {
            actualMin = Math.min(...valuesInBin);
            actualMax = Math.max(...valuesInBin);

            if (isBadPatch) {
              // For bad patch metrics, display as percentages
              rangeText = `${(actualMin * 100).toFixed(1)}%-${(actualMax * 100).toFixed(1)}%`;
            } else {
              // For regular metrics
              rangeText = `${actualMin.toFixed(1)}-${actualMax.toFixed(1)}${metric.unit}`;
            }
          } else {
            // Fallback to theoretical bin range if no actual values
            const binEndDisplay = binValue + binWidth;
            if (isBadPatch) {
              rangeText = `${binValue.toFixed(1)}%-${(binValue + binWidth * 100).toFixed(1)}%`;
            } else {
              rangeText = `${binValue.toFixed(1)}-${binEndDisplay.toFixed(1)}${metric.unit}`;
            }
          }

          return `Range: ${rangeText}<br/>Count: ${param.value}`;
        },
      },
      grid: processedData.metricsConfig.map((_, index) => {
        const row = Math.floor(index / 3);
        const col = index % 3;
        return {
          id: index.toString(),
          containLabel: true,
          top: `${3 + row * 33}%`,
          height: '26%',
          left: `${3 + col * 33}%`,
          width: '26%',
          bottom: '20%',
          show: true,
          padding: [15, 0, 15, 0],
          offset: 8,
        };
      }),
      xAxis: processedData.metricsConfig.map((metric, index) => {
        const [min, max] = metric.range;
        const bins = calculateBins(metric.values.length);
        const binWidth = (max - min) / bins;
        const isBadPatch = metric.key.includes('bad_patch');

        return {
          gridId: index.toString(),
          type: 'category',
          name: `${metric.label} ${metric.unit}`,
          nameLocation: 'middle',
          nameGap: 34,
          nameTextStyle: {
            fontSize: 14,
            padding: [0, 0, 0, 0],
            fontWeight: 'bold',
          },
          data: Array.from({ length: bins }, (_, i) => {
            const binStart = min + i * binWidth;
            return isBadPatch ? `${(binStart * 100).toFixed(1)}` : `${binStart.toFixed(1)}`;
          }),
          axisLabel: {
            interval: Math.floor(bins / 4),
            fontSize: 15,
          },
          axisTick: { show: false },
          splitLine: { show: false },
        };
      }),
      yAxis: processedData.metricsConfig.map((_, index) => {
        return {
          gridId: index.toString(),
          type: 'value',
          name: 'Number of tomograms',
          nameLocation: 'middle',
          nameGap: 42,
          nameTextStyle: {
            fontSize: 14,
            padding: [0, 0, 5, 0],
          },
          axisLine: {
            show: false,
          },
          axisTick: {
            show: false,
          },
          axisLabel: {
            show: true,
            formatter: (value: number) => Math.floor(value),
          },
          splitLine: { show: false },
        };
      }),
      series: processedData.metricsConfig.map((metric, index) => {
        const [min, max] = metric.range;
        const bins = calculateBins(metric.values.length);
        const binWidth = (max - min) / bins;
        const histogramData = Array(bins).fill(0);

        metric.values.forEach((value) => {
          const binIndex = Math.min(Math.floor((value - min) / binWidth), bins - 1);
          histogramData[binIndex]++;
        });

        return {
          name: metric.label,
          type: 'bar',
          xAxisIndex: index,
          yAxisIndex: index,
          data: histogramData,
          barWidth: '90%',
          itemStyle: {
            color: HISTOGRAM_METRIC_COLORS[metric.key as keyof typeof HISTOGRAM_METRIC_COLORS],
            opacity: 0.8,
          },
        };
      }),
    };

    chartInstance.current.setOption(option);
  }, [data, processedData]);

  useEffect(() => {
    const handleResize = () => {
      chartInstance.current?.resize();
    };

    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  return <div className={styles.histogramContainer} ref={chartRef} />;
};
