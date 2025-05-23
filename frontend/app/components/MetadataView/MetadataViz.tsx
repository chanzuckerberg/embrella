import React from 'react';
import styles from './MetadataViz.module.css';
import { MetadataFilters } from './MetadataFilters';
import { MetadataVizResponse, FilterConfig } from '@app/common/types/metadataViz/metadataVizData';
import { MetricDashboard } from './MetricDashBoard';
import { MetadataSummaryResponse } from '@app/common/types/metadataViz/metadataSummary';

interface MetadataVizProps {
  vizResponse?: MetadataVizResponse;
  isSuccess: boolean;
  error?: { status: number; message: string };
  isLoading: boolean;
  onApplyFilters?: (filters: FilterConfig, selectedOption: 'AND' | 'OR') => void;
  scatterplotData?: MetadataVizResponse;
  scatterplotSuccess?: boolean;
  scatterplotError?: { status: number; message: string };
  scatterplotLoading?: boolean;
  summaryAPIData?: MetadataSummaryResponse;
}

export const MetadataViz: React.FC<MetadataVizProps> = ({
  vizResponse,
  isSuccess,
  error,
  isLoading,
  onApplyFilters,
  scatterplotData,
  scatterplotSuccess,
  scatterplotError,
  scatterplotLoading,
  summaryAPIData,
}) => {
  if (isLoading) {
    return <div>Loading...</div>;
  }

  if (error) {
    return <div>Error: {error.message}</div>;
  }

  if (!isSuccess || !vizResponse) {
    return <div>No data available</div>;
  }
  return (
    <div className={styles.container}>
      <div className={styles.leftColumn}>
        <MetadataFilters
          metricRanges={vizResponse?.metric_ranges}
          onApplyFilters={onApplyFilters}
          summaryAPIData={summaryAPIData}
        />
      </div>
      <div className={styles.middleColumn}>
        <MetricDashboard
          data={vizResponse}
          scatterplotData={scatterplotData}
          scatterplotSuccess={scatterplotSuccess}
          scatterplotError={scatterplotError}
          scatterplotLoading={scatterplotLoading}
        />
      </div>
    </div>
  );
};
