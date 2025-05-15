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
  const [filters, setFilters] = useState<FilterConfig | undefined>();
  const { data, isSuccess, error, isLoading } = useFetchMetadataViz(sessionName, runNumber,filters);

  const handleApplyFilters = useCallback((newFilters: FilterConfig) => {
    setFilters(newFilters);

  }, []);
console.log(filters,'filters and filterdata', data);
  return (
    <div>
      <MetadataSummary sessionName={sessionName} runNumber={runNumber} />
      <MetadataViz vizResponse={data} isSuccess={isSuccess} error={error} isLoading={isLoading}  onApplyFilters={handleApplyFilters}
      />
    </div>
  );
};
