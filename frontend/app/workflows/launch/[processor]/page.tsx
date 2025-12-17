'use client';

/**
 * Dynamic processor launch page
 *
 * Route: /workflows/launch/[processor]
 * Examples:
 *   /workflows/launch/aretomo3
 *   /workflows/launch/denoiset
 *   /workflows/launch/copick
 */

import { Alert, CircularProgress } from '@mui/material';
import { PageContainer } from '@app/common/components/PageContainer';
import { useParams } from 'next/navigation';
import { useEffect, useState } from 'react';
import { fetchProcessorSchema } from '@app/common/services/workflowApi';
import type { ProcessorSchema } from '@app/common/types/workflow';
import WorkflowLaunchForm from '../components/WorkflowLaunchForm';
import AreTomo3LaunchForm from '../components/AreTomo3LaunchForm';
import DenoisETLaunchForm from '../components/DenoisETLaunchForm';
import CopickLaunchForm from '../components/CopickLaunchForm';
import MembranesegLaunchForm from '../components/MembranesegLaunchForm';

// Import processor-specific components
interface ProcessorFormComponentProps {
  processor: {
    name: string;
    display_name: string;
    version: string;
    default_cluster: string;
    allowed_clusters: string[];
  };
  schema: ProcessorSchema;
  cluster: 'czii' | 'bruno';
}
const PROCESSOR_COMPONENTS: Record<string, React.ComponentType<ProcessorFormComponentProps>> = {
  aretomo3: AreTomo3LaunchForm,
  denoiset: DenoisETLaunchForm,
  copick: CopickLaunchForm,
  membraneseg: MembranesegLaunchForm,
};

export default function ProcessorLaunchPage() {
  const params = useParams();
  const processorName = params.processor as string;

  const [schema, setSchema] = useState<ProcessorSchema | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedCluster, setSelectedCluster] = useState<'czii' | 'bruno'>('czii');

  // Load processor schema
  useEffect(() => {
    const loadSchema = async () => {
      try {
        setIsLoading(true);
        setError(null);
        const result = await fetchProcessorSchema(processorName);
        setSchema(result);
        // Set default cluster from schema
        if (result.default_cluster) {
          setSelectedCluster(result.default_cluster as 'czii' | 'bruno');
        }
        setIsLoading(false);
      } catch (err) {
        console.error('Failed to load processor schema:', err);
        setError(err instanceof Error ? err.message : `Failed to load processor: ${processorName}`);
        setIsLoading(false);
      }
    };

    if (processorName) {
      loadSchema();
    }
  }, [processorName]);

  // Loading state
  if (isLoading) {
    return (
      <PageContainer>
        <div style={{ display: 'flex', justifyContent: 'center', padding: '40px' }}>
          <CircularProgress />
        </div>
      </PageContainer>
    );
  }

  // Error state
  if (error || !schema) {
    return (
      <PageContainer>
        <Alert severity="error">{error || 'Failed to load processor configuration'}</Alert>
      </PageContainer>
    );
  }

  // Check if processor has a custom component
  const ProcessorComponent = PROCESSOR_COMPONENTS[processorName];

  return (
    <PageContainer>
      {ProcessorComponent ? (
        <ProcessorComponent
          processor={{
            name: schema.processor,
            display_name: schema.display_name,
            version: schema.version,
            default_cluster: schema.default_cluster,
            allowed_clusters: schema.allowed_clusters,
          }}
          schema={schema}
          cluster={selectedCluster}
        />
      ) : (
        <WorkflowLaunchForm
          processor={{
            name: schema.processor,
            display_name: schema.display_name,
            version: schema.version,
            default_cluster: schema.default_cluster,
            allowed_clusters: schema.allowed_clusters,
          }}
          schema={schema}
          cluster={selectedCluster}
        />
      )}
    </PageContainer>
  );
}
