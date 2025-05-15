import React from 'react';
import styles from './MetadataViz.module.css';
import { MetadataFilters } from './MetadataFilters';
import { MetadataVizResponse, FilterConfig } from '@app/common/types/metadataViz/metadataVizData';
import { MetricDashboard } from './MetricDashBoard';

interface MetadataVizProps {
  vizResponse?: MetadataVizResponse;
  isSuccess: boolean;
  error?: { status: number; message: string };
  isLoading: boolean;
  onApplyFilters?: (filters: FilterConfig, selectedOption: 'AND' | 'OR') => void;
}

export const MetadataViz: React.FC<MetadataVizProps> = ({ vizResponse, isSuccess, error, isLoading,onApplyFilters }) => {
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
        <MetadataFilters metricRanges={vizResponse?.metric_ranges} onApplyFilters={onApplyFilters} />
      </div>
      <div className={styles.middleColumn}>
        <MetricDashboard data={vizResponse} />
      </div>
    </div>
  );
};
