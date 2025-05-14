import React, { useState } from 'react';
import { MetadataVizResponse } from '../../common/types/metadataViz/metadataVizData';
import styles from './MetadataViz.module.css';
import { Switch, FormControlLabel, Box } from '@mui/material';
import { MetricScatterPlot } from './MetricScatterPlot';
import { MetricHistogram } from './MetricHistogram';

// Object defining various metrics with their labels and units
const METRICS_CONFIG = {
  thickness_pix: { label: 'Thickness', unit: '(Å)' },
  tilt_axis: { label: 'Tilt axis', unit: '(°)' },
  global_shift_pix: { label: 'Global shift', unit: '(Å)' },
  bad_patch_low: { label: 'Bad patch low', unit: '(%)' },
  bad_patch_all: { label: 'Bad patch all', unit: '(%)' },
  ctf_resolution_a: { label: 'CTF Resolution', unit: '(Å)' },
  ctf_score: { label: 'CTF CC Score', unit: '' },
  alpha0: { label: 'Alpha Offset', unit: '(°)' },
  beta0: { label: 'Beta Offset', unit: '(°)' },
};

interface MetricDashboardProps {
  data?: MetadataVizResponse;
  // selectedPosition?: number;
}

export const MetricDashboard: React.FC<MetricDashboardProps> = ({ data }) => {
  console.log(data, 'data');
  const [isHistogram, setIsHistogram] = useState(true);

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
          control={<Switch checked={isHistogram} onChange={(e) => setIsHistogram(e.target.checked)} color="primary" />}
          label={isHistogram ? 'Histogram View' : 'Scatter Plot View'}
        />
      </Box>
      {processedData ? (
        data ? (
          isHistogram ? (
            <MetricHistogram data={data} processedData={processedData} />
          ) : (
            <MetricScatterPlot data={data} processedData={processedData} />
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
