'use client';

import React, { useCallback, useState } from 'react';
import { MetadataSummary } from './MetadataSummary';
import { MetadataViz } from './MetadataViz';
import { useFetchMetadataViz } from '@app/common/hooks/useFetchMetadata/useFetchMetadataViz';
import { FilterConfig } from '@app/common/types/metadataViz/metadataVizData';

interface MetadataViewProps {
  sessionName: string;
  runNumber: string;
}

export const MetadataView = ({ sessionName, runNumber }: MetadataViewProps): React.JSX.Element => {
  const [isFilterApplied, setIsFilterApplied] = useState(false);
  const [filters] = useState<FilterConfig | undefined>();
  const [scatterplotFilters, setScatterplotFilters] = useState<FilterConfig | undefined>();

  // This API call is for the metadata filters and histogram
  const { data, isSuccess, error, isLoading } = useFetchMetadataViz(sessionName, runNumber, filters);

  // This API call is only for the scatterplot
  const {
    data: scatterplotData,
    isSuccess: scatterplotSuccess,
    error: scatterplotError,
    isLoading: scatterplotLoading,
  } = useFetchMetadataViz(sessionName, runNumber, scatterplotFilters);

  const handleApplyFilters = useCallback((newFilters: FilterConfig | null) => {
    // Force a state update by creating a new object reference
    if (newFilters === null) {
      // Reset case
      setScatterplotFilters(undefined);
      setIsFilterApplied(false);
    } else {
      // Apply new filters - create a new object to ensure React detects the change
      setScatterplotFilters({ ...newFilters });
      // Check if there are any active filters
      const hasActiveFilters = newFilters.filters && Object.keys(newFilters.filters).length > 0;
      setIsFilterApplied(hasActiveFilters);
    }
  }, []);

  return (
    <div>
      <MetadataSummary
        sessionName={sessionName}
        runNumber={runNumber}
        isFilterApplied={isFilterApplied}
        filteredData={scatterplotData}
      />
      <MetadataViz
        vizResponse={data}
        isSuccess={isSuccess}
        error={error}
        isLoading={isLoading}
        onApplyFilters={handleApplyFilters}
        scatterplotData={scatterplotData}
        scatterplotSuccess={scatterplotSuccess}
        scatterplotError={scatterplotError}
        scatterplotLoading={scatterplotLoading}
      />
    </div>
  );
};
