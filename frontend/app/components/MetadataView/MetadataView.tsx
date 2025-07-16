'use client';

import React, { useCallback, useState } from 'react';
import { MetadataSummary } from './MetadataSummary';
import { MetadataViz } from './MetadataViz';
import { useFetchMetadataViz } from '@app/common/hooks/useFetchMetadata/useFetchMetadataViz';
import { useFetchMetadataSummary } from '@app/common/hooks/useFetchMetadata/useFetchMetadataSummary';
import { FilterConfig } from '@app/common/types/metadataViz/metadataVizData';
import { useFilterState } from '@app/common/hooks/useFetchMetadata/useFilterState';
import { METRICS_CONFIG } from './constants/MetricConfig';
import { MetricRanges } from '@app/common/types/metadataViz/metadataVizData';

interface MetadataViewProps {
  sessionName: string;
  runNumber: string;
}

export const MetadataView = ({ sessionName, runNumber }: MetadataViewProps): React.JSX.Element => {
  const [isFilterApplied, setIsFilterApplied] = useState(false);
  const [scatterplotFilters, setScatterplotFilters] = useState<FilterConfig | undefined>();
  const [shouldFetchSummary, setShouldFetchSummary] = useState(true);

  // This API call is for the metadata summary
  const {
    data: summaryData,
    isSuccess: summarySuccess,
    error: summaryError,
    isLoading: summaryLoading,
  } = useFetchMetadataSummary(sessionName, runNumber, shouldFetchSummary);

  const handleToggleSummary = useCallback(() => {
    setShouldFetchSummary(true);
  }, []);

  // This API call is for the metadata filters and histogram
  const { data, isSuccess, error, isLoading } = useFetchMetadataViz(sessionName, runNumber);

  // This API call is only for the scatterplot
  const {
    data: scatterplotData,
    isSuccess: scatterplotSuccess,
    error: scatterplotError,
    isLoading: scatterplotLoading,
  } = useFetchMetadataViz(sessionName, runNumber, scatterplotFilters);

  // Handle filter state changes from the filter hook
  const handleFilterStateChange = useCallback((filterApplied: boolean, filterConfig?: FilterConfig) => {
    setIsFilterApplied(filterApplied);

    // Force a state update by creating a new object reference
    if (filterApplied && filterConfig) {
      setScatterplotFilters({ ...filterConfig });
    } else {
      setScatterplotFilters(undefined);
    }
  }, []);
  // Create a default MetricRanges object with all required properties
  const defaultMetricRanges = React.useMemo((): MetricRanges => {
    return {
      thickness: [0, 0],
      tilt_axis: [0, 0],
      global_shift: [0, 0],
      bad_patch_low: [0, 0],
      bad_patch_all: [0, 0],
      ctf_resolution: [0, 0],
      ctf_score: [0, 0],
      defocus: [0, 0],
      extphase: [0, 0],
      pixel_size: [0, 0],
      alpha0: [0, 0],
      beta0: [0, 0],
    };
  }, []);

  // Initialize the filter state hook
  const filterState = useFilterState({
    metricRanges: data?.metric_ranges || (defaultMetricRanges as MetricRanges),
    metricsConfig: METRICS_CONFIG,
    initialFilterType: 'AND',
    onFilterStateChange: handleFilterStateChange,
    summaryAPIData: summaryData,
  });

  return (
    <div>
      <MetadataSummary
        isFilterApplied={isFilterApplied}
        filteredData={scatterplotData}
        summaryAPIData={summaryData}
        summaryError={summaryError}
        summaryLoading={summaryLoading}
        summarySuccess={summarySuccess}
        onToggleSummary={handleToggleSummary}
      />
      <MetadataViz
        vizResponse={data}
        isSuccess={isSuccess}
        error={error}
        isLoading={isLoading}
        filterState={filterState}
        summaryAPIData={summaryData}
        scatterplotData={scatterplotData}
        scatterplotSuccess={scatterplotSuccess}
        scatterplotError={scatterplotError}
        scatterplotLoading={scatterplotLoading}
      />
    </div>
  );
};
