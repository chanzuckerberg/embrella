import React, { useState } from 'react';
import { MetadataVizResponse } from '../../common/types/metadataViz/metadataVizData';
import styles from './MetadataViz.module.css';
import { Switch, FormControlLabel, Box } from '@mui/material';
import { MetricScatterPlot } from './MetricScatterPlot';
import { MetricHistogram } from './MetricHistogram';
import { METRICS_CONFIG } from './constants/MetricConfig';

interface MetricDashboardProps {
  data?: MetadataVizResponse;
  scatterplotData?: MetadataVizResponse;
  scatterplotSuccess?: boolean;
  scatterplotError?: { status: number; message: string };
  scatterplotLoading?: boolean;
}

// Helper function to process metadata
const processMetadata = (data: MetadataVizResponse | undefined) => {
  if (!data?.accepted_results?.length) return null;

  const processedMetrics = Object.keys(METRICS_CONFIG).map((key) => {
    const metricKey = key as keyof typeof METRICS_CONFIG;
    const values = data.accepted_results.map((item) => {
      return item.metrics[metricKey];
    });

    return {
      key,
      label: METRICS_CONFIG[metricKey].label,
      unit: METRICS_CONFIG[metricKey].unit,
      values,
      range: data.metric_ranges[metricKey],
    };
  });

  return {
    metricsConfig: processedMetrics,
    totalPositions: data.accepted_results.length,
  };
};

// Helper function to check if filters are applied
const checkFiltersApplied = (scatterplotData: MetadataVizResponse | undefined) => {
  return (
    !!scatterplotData &&
    scatterplotData.filters_applied?.filters !== null &&
    scatterplotData.filters_applied?.filters !== undefined &&
    Object.keys(scatterplotData.filters_applied?.filters || {}).length > 0
  );
};

export const MetricDashboard: React.FC<MetricDashboardProps> = ({
  data,
  scatterplotData,
  scatterplotError,
  scatterplotLoading,
}) => {
  const [isScatterPlot, setIsScatterPlot] = useState(true);

  // Process data once for both visualizations
  const processedData = React.useMemo(() => processMetadata(data), [data]);

  // Process scatterplot data separately
  const processedScatterplotData = React.useMemo(() => processMetadata(scatterplotData), [scatterplotData]);

  // Determine which data to use for the scatterplot
  const scatterplotDisplayData = scatterplotData || data;
  const scatterplotProcessedData = processedScatterplotData || processedData;
  const isScatterplotLoading = scatterplotLoading || false;
  const hasScatterplotError = scatterplotError || false;

  // Determine if filters are applied
  const isFilterApplied = checkFiltersApplied(scatterplotData);

  // Helper function to render the appropriate visualization
  const renderVisualization = () => {
    if (!processedData) {
      return <></>;
    }

    if (!data) {
      return <div className={styles.noDataMessage}>No data available</div>;
    }

    if (isScatterPlot) {
      if (scatterplotDisplayData && scatterplotProcessedData) {
        return (
          <MetricScatterPlot
            data={scatterplotDisplayData}
            processedData={scatterplotProcessedData}
            isLoading={isScatterplotLoading}
            error={hasScatterplotError}
            isFilterApplied={isFilterApplied}
          />
        );
      }
      return <div>No data available for scatter plot</div>;
    }

    return <MetricHistogram data={data} processedData={processedData} />;
  };

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
      {renderVisualization()}
    </div>
  );
};