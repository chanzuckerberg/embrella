'use client';

import {
  Alert,
  Box,
  Card,
  CardContent,
  CircularProgress,
  FormControl,
  FormHelperText,
  InputLabel,
  MenuItem,
  Paper,
  Select,
  SelectChangeEvent,
  Typography,
} from '@mui/material';
import { PageContainer } from '@app/common/components/PageContainer';
import { useEffect, useState } from 'react';
import { listProcessors, fetchProcessorSchema } from '@app/common/services/workflowApi';
import type { Processor, ProcessorSchema } from '@app/common/types/workflow';
import AreTomo3LaunchForm from './components/AreTomo3LaunchForm';
import DenoisETLaunchForm from './components/DenoisETLaunchForm';
import CopickLaunchForm from './components/CopickLaunchForm';
import MembranesegLaunchForm from './components/MembranesegLaunchForm';
import { ClusterSelector } from '@app/common/components/ClusterSelector';
import { SSHSetupModal } from '@app/common/components/SSHSetupModal';

export default function WorkflowLaunchPage() {
  const [processors, setProcessors] = useState<Processor[]>([]);
  const [selectedProcessor, setSelectedProcessor] = useState<string>('');
  const [selectedProcessorData, setSelectedProcessorData] = useState<Processor | null>(null);
  const [selectedCluster, setSelectedCluster] = useState<string>('');
  const [schema, setSchema] = useState<ProcessorSchema | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [schemaLoading, setSchemaLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sshSetupModalOpen, setSSHSetupModalOpen] = useState(false);
  const [currentUsername, setCurrentUsername] = useState<string>('');
  const [recheckAccessTrigger, setRecheckAccessTrigger] = useState(0);

  // Load processors on mount
  useEffect(() => {
    const loadProcessors = async () => {
      try {
        setIsLoading(true);
        const processorList = await listProcessors();
        setProcessors(processorList);
        setIsLoading(false);
      } catch (err) {
        console.error('Failed to load processors:', err);
        setError(err instanceof Error ? err.message : 'Failed to load processors');
        setIsLoading(false);
      }
    };

    loadProcessors();
  }, []);

  // Handle processor selection
  const handleProcessorChange = async (event: SelectChangeEvent<string>) => {
    const processorName = event.target.value;
    setSelectedProcessor(processorName);
    setSchema(null);

    if (!processorName) {
      setSelectedProcessorData(null);
      setSelectedCluster('');
      return;
    }

    // Find processor data
    const processor = processors.find((p) => p.name === processorName);
    if (processor) {
      setSelectedProcessorData(processor);
      setSelectedCluster(processor.default_cluster);

      // Fetch schema
      try {
        setSchemaLoading(true);
        const schemaData = await fetchProcessorSchema(processorName);
        setSchema(schemaData);
      } catch (err) {
        console.error('Failed to load schema:', err);
        setError(err instanceof Error ? err.message : 'Failed to load schema');
      } finally {
        setSchemaLoading(false);
      }
    }
  };

  // Handle cluster selection
  const handleClusterChange = (cluster: 'czii' | 'bruno') => {
    setSelectedCluster(cluster);
  };

  // SSH setup required handler (called by ClusterSelector)
  const handleSSHSetupRequired = (cluster: 'czii' | 'bruno', username: string) => {
    setCurrentUsername(username);
    setSSHSetupModalOpen(true);
  };

  // SSH setup success handler
  const handleSSHSetupSuccess = () => {
    setSSHSetupModalOpen(false);
    // Trigger a re-check of SSH access to show success message
    setRecheckAccessTrigger((prev) => prev + 1);
  };

  // Render the appropriate processor-specific form
  const renderProcessorForm = () => {
    if (!selectedProcessorData || !schema) return null;

    const commonProps = {
      processor: selectedProcessorData,
      schema,
      cluster: selectedCluster as 'czii' | 'bruno',
      onSubmit: () => {
        // Success handled by individual forms
      },
    };

    switch (selectedProcessor) {
      case 'aretomo3':
        return <AreTomo3LaunchForm {...commonProps} />;
      case 'denoiset':
        return <DenoisETLaunchForm {...commonProps} />;
      case 'copick':
        return <CopickLaunchForm {...commonProps} />;
      case 'membraneseg':
        return <MembranesegLaunchForm {...commonProps} />;
      default:
        // Fallback for unknown processors - could render a generic form
        return (
          <Alert severity="warning" sx={{ mt: 3 }}>
            <Typography variant="body1">
              Processor &quot;{selectedProcessor}&quot; does not have a dedicated form. Please use the generic workflow
              launcher.
            </Typography>
          </Alert>
        );
    }
  };

  // Loading state
  if (isLoading) {
    return (
      <PageContainer>
        <Box display="flex" justifyContent="center" alignItems="center" minHeight="50vh">
          <CircularProgress />
        </Box>
      </PageContainer>
    );
  }

  // Error state
  if (error && processors.length === 0) {
    return (
      <PageContainer>
        <Alert severity="error">{error}</Alert>
      </PageContainer>
    );
  }

  return (
    <PageContainer>
      <Paper sx={{ p: 4, mb: 3 }}>
        <Typography variant="h4" gutterBottom>
          Launch a processing job
        </Typography>
        <Typography variant="body1" paragraph>
          Select a processing workflow, configure parameters, and submit a job to the cluster.
        </Typography>
      </Paper>

      {!!error && (
        <Alert severity="error" sx={{ mb: 3 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            1. Select Processor
          </Typography>

          <FormControl fullWidth margin="normal">
            <InputLabel>Processor</InputLabel>
            <Select value={selectedProcessor} onChange={handleProcessorChange} disabled={isLoading}>
              {processors.map((processor) => (
                <MenuItem key={processor.name} value={processor.name}>
                  {processor.display_name} v{processor.version} (default: {processor.default_cluster})
                </MenuItem>
              ))}
            </Select>
            <FormHelperText>Choose the processing software to execute</FormHelperText>
          </FormControl>

          {selectedProcessorData && selectedProcessorData.allowed_clusters.length > 0 && (
            <Box sx={{ mt: 2 }}>
              <ClusterSelector
                value={selectedCluster as 'czii' | 'bruno'}
                onChange={handleClusterChange}
                showCheckAccess={true}
                onSSHSetupRequired={handleSSHSetupRequired}
                disabled={selectedProcessorData.allowed_clusters.length === 1}
                recheckTrigger={recheckAccessTrigger}
              />
              {selectedProcessorData.allowed_clusters.length === 1 && (
                <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 1 }}>
                  Only one cluster available for this processor
                </Typography>
              )}
            </Box>
          )}

          {schemaLoading && (
            <Box display="flex" justifyContent="center" my={3}>
              <CircularProgress size={30} />
            </Box>
          )}

          {!!selectedProcessor && !schemaLoading && schema && <Box sx={{ mt: 4 }}>{renderProcessorForm()}</Box>}
        </CardContent>
      </Card>

      {processors.length === 0 && !isLoading && (
        <Alert severity="warning" sx={{ mt: 3 }}>
          <Typography variant="body1">
            No processors available. Make sure the backend is running and processors are configured.
          </Typography>
        </Alert>
      )}

      {/* SSH Setup Modal */}
      {!!currentUsername && (
        <SSHSetupModal
          open={sshSetupModalOpen}
          onClose={() => setSSHSetupModalOpen(false)}
          onSuccess={handleSSHSetupSuccess}
          cluster={selectedCluster as 'czii' | 'bruno'}
          username={currentUsername}
        />
      )}
    </PageContainer>
  );
}
