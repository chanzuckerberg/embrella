import React from 'react';
import styles from './MetadataViz.module.css';
import { MetadataFilters } from './MetadataFilters';
import { MetadataVizResponse } from '@app/common/types/metadataViz/metadataVizData';

interface MetadataVizProps {
  vizResponse?: MetadataVizResponse;
  isSuccess: boolean;
  error?: { status: number; message: string };
  isLoading: boolean;
}

export const MetadataViz: React.FC<MetadataVizProps> = ({ vizResponse, isSuccess, error, isLoading }) => {
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
        <MetadataFilters metricRanges={vizResponse?.metric_ranges} />
      </div>
      <div className={styles.middleColumn}>
        <h2>AreTomo Metrics Dashboard</h2>
        {/* Add visualization components here */}
      </div>
    </div>
  );
};
