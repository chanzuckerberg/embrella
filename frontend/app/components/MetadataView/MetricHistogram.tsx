import React, { useEffect, useRef } from 'react';
import * as echarts from 'echarts';
import { MetadataVizResponse } from '../../common/types/metadataViz/metadataVizData';
import styles from './MetadataViz.module.css';

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

// Color mapping for different metrics (same as scatter plot)
const METRIC_COLORS = {
  thickness_pix: '#1f77b4',
  tilt_axis: '#ff7f0e',
  global_shift_pix: '#9467bd',
  bad_patch_low: '#8c564b',
  bad_patch_all: '#e377c2',
  ctf_resolution_a: '#17becf',
  ctf_score: '#ffd700',
};

// Sturges' formula for calculating number of bins
const calculateBins = (n: number): number => {
  return Math.ceil(1 + 3.322 * Math.log10(n));
};

export const MetricHistogram: React.FC<MetricHistogramProps> = ({ data, processedData }) => {
  console.log(processedData, 'processedData');
  const chartRef = useRef<HTMLDivElement>(null);
  const chartInstance = useRef<echarts.ECharts>();

  useEffect(() => {
    if (!chartRef.current || !data?.result) return;

    if (!chartInstance.current) {
      chartInstance.current = echarts.init(chartRef.current);
    }

    const option: echarts.EChartsOption = {
      tooltip: processedData.metricsConfig.map((metric) => ({
        trigger: 'item',
        formatter: function (params: echarts.TooltipComponentFormatterCallbackParams) {
          // Ensure params is treated as a single item, not an array
          const param = Array.isArray(params) ? params[0] : params;
          const binValue = parseFloat(param.name);
          const isBadPatch = param.seriesName?.toLowerCase().includes('bad patch');
          const binWidth = (metric.range[1] - metric.range[0]) / calculateBins(metric.values.length);
          const binEnd = binValue + binWidth;
          const value = param.value;
          const rangeText = isBadPatch
            ? `${binValue.toFixed(1)}%-${(binEnd * 100).toFixed(1)}%`
            : `${binValue.toFixed(1)}-${binEnd.toFixed(1)}`;
          return `Range: ${rangeText}<br/>Count: ${value}`;
        },
      })),
      grid: processedData.metricsConfig.map((_, index) => {
        const row = Math.floor(index / 3);
        const col = index % 3;
        return {
          id: index.toString(),
          containLabel: true,
          top: `${4 + row * 33}%`,
          height: '26%',
          left: `${4 + col * 32}%`,
          width: '26%',
          bottom: '20%',
          show: true,
          padding: [15, 10, 15, 0],
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
            color: METRIC_COLORS[metric.key as keyof typeof METRIC_COLORS],
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
