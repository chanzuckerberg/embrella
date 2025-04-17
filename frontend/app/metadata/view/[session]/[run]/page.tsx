import React from 'react';
import { MetadataView } from '@app/components/MetadataView/MetadataView';

interface MetadataPageProps {
  params: {
    id: string;
  };
}

export default function MetadataPage({ params }: MetadataPageProps) {
  return <MetadataView sessionId={params.id}  />;
}