import React, { memo, useState } from 'react';
import styles from './MetadataViz.module.css';
import { MetadataFilters } from './MetadataFilters';
import { MetadataVizResponse } from '@app/common/types/metadataViz/metadataVizData';
import { MetricDashboard } from './MetricDashBoard';
import { ThumbnailGrid } from './ThumbnailGrid';
import { MetadataSummaryResponse } from '@app/common/types/metadataViz/metadataSummary';
import { UseFilterStateReturn } from '@app/common/hooks/useFetchMetadata/useFilterState';
import NanoScaleBar from './utils/NanoScaleBar';

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
    // State to track which position is being hovered in thumbnails
    const [hoveredPosition, setHoveredPosition] = useState<string | null>(null);
    
    const handleThumbnailHover = (positionName: string | null) => {
      setHoveredPosition(positionName);
    };
    
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
            hoveredPosition={hoveredPosition}
            onHoverPosition={handleThumbnailHover}
          />
        </div>
        <div className={styles.rightColumn}>
          <NanoScaleBar angstrom={summaryAPIData?.pixel_size||0} />
          <ThumbnailGrid
            acceptedResults={vizResponse.accepted_results}
            rejectedResults={vizResponse.rejected_results}
            data={vizResponse}
            onThumbnailHover={handleThumbnailHover}
            hoveredPosition={hoveredPosition}
          />
        </div>
      </div>
    );
  }
);
MetadataViz.displayName = 'MetadataViz';