import React from 'react';
import { Metadata } from 'next';
import { MetadataView } from '@app/components/MetadataView/MetadataView';

export const metadata: Metadata = {
  title: 'Metadata View',
};

interface MetadataPageProps {
  params: Promise<{
    session: string;
    run: string;
  }>;
}

export default async function MetadataPage({ params }: MetadataPageProps) {
  const { session, run } = await params;
  return <MetadataView sessionName={session} runNumber={run} />;
}
