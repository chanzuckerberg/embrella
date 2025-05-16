import React, { useState } from 'react';
import { MetadataVizResponse } from '../../common/types/metadataViz/metadataVizData';
import styles from './MetadataViz.module.css';
import { Switch, FormControlLabel, Box } from '@mui/material';
import { MetricScatterPlot } from './MetricScatterPlot';
import { MetricHistogram } from './MetricHistogram';
import { METRICS_CONFIG } from './constants/MetricConfig';

interface MetricDashboardProps {
  data?: MetadataVizResponse;
  // selectedPosition?: number;
}

export const MetricDashboard: React.FC<MetricDashboardProps> = ({ data }) => {
  console.log(data, 'Dashboarddata');
  const [isScatterPlot, setIsScatterPlot] = useState(true);

  // Process data once for both visualizations
  const processedData = React.useMemo(() => {
    if (!data?.accepted_results?.length) return null;

    // Filter to only include the metrics we want to show
    const metricsConfig = Object.keys(METRICS_CONFIG).map((key) => ({
      key,
      label: METRICS_CONFIG[key as keyof typeof METRICS_CONFIG].label,
      unit: METRICS_CONFIG[key as keyof typeof METRICS_CONFIG].unit,
    }));

    const processedMetrics = metricsConfig.map((metric) => {
      const values = data.accepted_results.map((item) => {
        return item.metrics[metric.key as keyof typeof item.metrics];
      });

      return {
        ...metric,
        values,
        range: data.metric_ranges[metric.key as keyof typeof data.metric_ranges],
      };
    });

    return {
      metricsConfig: processedMetrics,
      totalPositions: data.accepted_results.length,
    };
  }, [data]);

  return (
    <div className={styles.dashboardContainer}>
      <Box display="flex" justifyContent="flex-end">
        <FormControlLabel
          control={
            <Switch checked={isScatterPlot} onChange={(e) => setIsScatterPlot(e.target.checked)} color="primary" />
          }
          label={isScatterPlot ? 'Scatter Plot View' : 'Histogram View'}
        />
      </Box>
      {processedData ? (
        data ? (
          isScatterPlot ? (
            <MetricScatterPlot data={data} processedData={processedData} />
          ) : (
            <MetricHistogram data={data} processedData={processedData} />
          )
        ) : (
          <div className={styles.noDataMessage}>No data available</div>
        )
      ) : (
        <></>
      )}
    </div>
  );
};
