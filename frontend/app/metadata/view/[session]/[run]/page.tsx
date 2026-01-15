import React from 'react';
import { Metadata } from 'next';
import { MetadataView } from '@app/components/MetadataView/MetadataView';

export const metadata: Metadata = {
  title: 'Metadata View',
};

interface MetadataPageProps {
  params: {
    session: string;
    run: string;
  };
}

export default function MetadataPage({ params }: MetadataPageProps) {
  return <MetadataView sessionName={params.session} runNumber={params.run} />;
}
