import React from 'react';
import { MetadataView } from '@app/components/MetadataView/MetadataView';

interface MetadataPageProps {
  params: {
    session: string;
    run: string;
  };
}

export default function MetadataPage({ params }: MetadataPageProps) {
  return <MetadataView sessionName={params.session} runNumber={params.run} />;
}
