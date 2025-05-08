import React, { useEffect, useRef } from 'react';
import * as echarts from 'echarts';
import { MetadataVizResponse, Metrics } from '../../common/types/metadataViz/metadataVizData';
import styles from './MetadataViz.module.css';

interface MetricScatterPlotProps {
  data: MetadataVizResponse;
  processedData: ProcessedData;
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

// Hardcoded units for metrics
const units = {
  thickness_pix: '(Pix)',
  tilt_axis: '(°)',
  global_shift_pix: '(Pix)',
  bad_patch_low: '(%)',
  bad_patch_all: '(%)',
  ctf_resolution_a: '(Å)',
  ctf_score: '',
};
const METRIC_COLORS = {
  thickness_pix: '#1f77b4',
  tilt_axis: '#ff7f0e',
  global_shift_pix: '#9467bd',
  bad_patch_low: '#8c564b',
  bad_patch_all: '#e377c2',
  ctf_resolution_a: '#17becf',
  ctf_score: '#ffd700',
};

// Helper to format metric key to label
const formatMetricLabel = (key: string): string => {
  return key
    .split('_')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
};

console.log('formatMetricLabel', formatMetricLabel);
// Sturges' formula for calculating number of bins
const calculateBins = (n: number): number => {
  return Math.ceil(1 + 3.322 * Math.log10(n));
};

export const MetricScatterPlot: React.FC<MetricScatterPlotProps> = ({ data, processedData }) => {
  const chartRef = useRef<HTMLDivElement>(null);
  const chartInstance = useRef<echarts.ECharts>();

  useEffect(() => {
    if (!chartRef.current || !data?.result) return;

    if (!chartInstance.current) {
      chartInstance.current = echarts.init(chartRef.current);
    }

    // Generate metrics config from the data
    const metricsConfig = Object.keys(data.metric_ranges)
      .filter((key) => key in units) // Only include metrics with defined units
      .map((key) => ({
        key,
        label: formatMetricLabel(key),
      }));

    const option: echarts.EChartsOption = {
      tooltip: {
        trigger: 'item',
        formatter: function (params: any) {
          const tiltSeries = data.result[params.dataIndex];
          const metrics = tiltSeries.metrics;

          let tooltipContent = `<div style="font-weight: bold; margin-bottom: 5px;">Position : ${tiltSeries.name}</div>`;

          // Helper function to format the metric line
          const formatMetricLine = (key: keyof Metrics, label: string, unit: string, multiplier = 1) => {
            const value = metrics[key] * multiplier;
            return `<div>${label}: ${value.toFixed(2)}${unit}</div>`;
          };

          // Add all metric values to tooltip
          tooltipContent += formatMetricLine('thickness_pix', 'Thickness', ' (Pix)');
          tooltipContent += formatMetricLine('tilt_axis', 'Tilt Axis', '°');
          tooltipContent += formatMetricLine('global_shift_pix', 'Global Shift', ' (Pix)');
          tooltipContent += formatMetricLine('bad_patch_low', 'Bad Patch Low', '%', 100);
          tooltipContent += formatMetricLine('bad_patch_all', 'Bad Patch All', '%', 100);
          tooltipContent += formatMetricLine('ctf_resolution_a', 'CTF Resolution', ' Å');
          tooltipContent += formatMetricLine('ctf_score', 'CTF Score', '');

          return tooltipContent;
        },
        backgroundColor: 'rgba(255, 255, 255, 0.95)',
        borderColor: '#ccc',
        borderWidth: 1,
        padding: [10, 15],
        textStyle: {
          color: '#333',
          fontSize: 13,
        },
      },
      grid: metricsConfig.map((_, index) => ({
        containLabel: true,
        top: `${2 + index * 14}%`,
        height: '11%',
        left: '6%',
        right: '10%',
        bottom: '20%',
        offset: 8,
        show: true,
        padding: [15, 0, 15, 0],
      })),
      xAxis: metricsConfig.map((metric, index) => ({
        type: 'value',
        gridIndex: index,
        name: 'Position',
        position: 'bottom',
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
          fontWeight: 'bold',
          wrap: true,
        },
        min: 0,
        max: data.result.length - 1,
        splitLine: {
          show: false,
        },
      })),
      yAxis: processedData.metricsConfig.map((metric, index) => {
        const values = data.result.map((item) => {
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
          type: 'value',
          gridIndex: index,
          name: `${metric.label} \n${metric.unit}`,
          nameLocation: 'middle',
          nameGap: 45,
          nameTextStyle: {
            fontSize: 14,
            fontWeight: 'bold',
            align: 'center',
            wrap: true,
            padding: [0, 0, 15, 0],
            margin: 8,
          },
          splitNumber: calculateBins(values),
          min: min - padding,
          max: max + padding,
          splitLine: {
            show: true,
            lineStyle: {
              type: 'dashed',
              opacity: 0.3,
            },
          },
          axisLabel: {
            show: true,
            margin: 8,
            fontSize: 10,
            formatter: (value: number) => value.toFixed(2),
          },
        };
      }),

      series: metricsConfig.map((metric, index) => ({
        type: 'scatter',
        name: metric.label,
        xAxisIndex: index,
        yAxisIndex: index,
        symbolSize: 4,
        itemStyle: {
          opacity: 0.6,
          color: METRIC_COLORS[metric.key as keyof typeof METRIC_COLORS],
        },
        data: data.result.map((item, pos) => {
          const value = item.metrics[metric.key as keyof Metrics];
          return [pos, metric.key.includes('bad_patch') ? value * 100 : value];
        }),
        ...(processedData !== undefined && {
          markPoint: {
            data: [
              {
                name: `Position_${processedData}`,
                coord: [
                  processedData,
                  metric.key.includes('bad_patch')
                    ? data.result[processedData]?.metrics[metric.key as keyof Metrics] * 100
                    : data.result[processedData]?.metrics[metric.key as keyof Metrics],
                ],
                symbol: 'arrow',
                symbolSize: 20,
                itemStyle: { color: '#666' },
                label: {
                  show: true,
                  formatter: `Position_${processedData}`,
                  position: 'top',
                },
              },
            ],
          },
        }),
      })),
    };

    chartInstance.current.setOption(option);
  }, [data, processedData]);

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
    <div className={styles.dashboardContainer}>
      {data ? (
        <div className={styles.chartContainer} ref={chartRef} />
      ) : (
        <div className={styles.noDataMessage}>{'No data available'}</div>
      )}
    </div>
  );
};
