'use client';

import React from 'react';
import { MetadataSummary } from './MetadataSummary';
// import { MetadataViz } from './MetadataViz';
// import { useFetchMetadataViz } from '@app/common/hooks/useFetchMetadata/useFetchMetadataViz';

interface MetadataViewProps {
  sessionName: string;
  runNumber: string;
}

export const MetadataView = ({ sessionName, runNumber }: MetadataViewProps): React.JSX.Element => {
  // const { data, isSuccess, error, isLoading } = useFetchMetadataViz(sessionName, runNumber);
  return (
    <div>
      <MetadataSummary sessionName={sessionName} runNumber={runNumber} />
      {/* <MetadataViz vizResponse={data} isSuccess={isSuccess} error={error} isLoading={isLoading} /> */}
    </div>
  );
};
