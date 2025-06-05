import React, { memo } from 'react';
import styles from './MetadataViz.module.css';
import { MetadataFilters } from './MetadataFilters';
import { MetadataVizResponse } from '@app/common/types/metadataViz/metadataVizData';
import { MetricDashboard } from './MetricDashBoard';
import { MetadataSummaryResponse } from '@app/common/types/metadataViz/metadataSummary';
import { UseFilterStateReturn } from '@app/common/hooks/useFetchMetadata/useFilterState';

interface MetadataVizProps {
  vizResponse?: MetadataVizResponse;
  isSuccess: boolean;
  error?: { status: number; message: string };
  isLoading: boolean;
  filterState: UseFilterStateReturn;
  scatterplotData?: MetadataVizResponse;
  scatterplotSuccess?: boolean;
  scatterplotError?: { status: number; message: string };
  scatterplotLoading?: boolean;
  summaryAPIData?: MetadataSummaryResponse;
}

/**
 * Component that renders the metadata visualization section
 * Includes filters and metric dashboard (scatter plot, histograms)
 */
export const MetadataViz: React.FC<MetadataVizProps> = memo(
  ({
    vizResponse,
    isSuccess,
    error,
    isLoading,
    filterState,
    summaryAPIData,
    scatterplotData,
    scatterplotSuccess,
    scatterplotError,
    scatterplotLoading,
  }) => {
    if (isLoading) {
      return <div>Loading...</div>;
    }

    if (error) {
      return <div>Error: {error instanceof Error ? error.message : 'An unknown error occurred'}</div>;
    }

    if (!isSuccess || !vizResponse) {
      return <div>No data available</div>;
    }

    return (
      <div className={styles.container}>
        <div className={styles.leftColumn}>
          <MetadataFilters
            metricRanges={vizResponse?.metric_ranges}
            filterState={filterState}
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
        <div className={styles.rightColumn}>
          <div>
            <h3>Position Details</h3>
            <p>Select a position on the scatter plot to view details</p>
          </div>
        </div>
      </div>
    );
  }
);
MetadataViz.displayName = 'MetadataViz';
