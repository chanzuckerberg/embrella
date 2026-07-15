'use client';

import { useParams } from 'next/navigation';
import { Alert, Box, CircularProgress, Container } from '@mui/material';

import { useDataset } from '../../hooks/useDataset';
import { WizardLayout } from '../WizardLayout';

export default function DepositionWizardPage() {
  const params = useParams<{ id: string }>();
  const id = Number(params.id);
  const { data, isPending, isError } = useDataset(Number.isFinite(id) ? id : null);

  if (!Number.isFinite(id)) {
    return (
      <Container maxWidth="lg" sx={{ py: 4 }}>
        <Alert severity="error">Invalid dataset id.</Alert>
      </Container>
    );
  }
  if (isPending) {
    return (
      <Container maxWidth="lg" sx={{ py: 6 }}>
        <Box sx={{ display: 'flex', justifyContent: 'center' }}>
          <CircularProgress />
        </Box>
      </Container>
    );
  }
  if (isError || !data) {
    return (
      <Container maxWidth="lg" sx={{ py: 4 }}>
        <Alert severity="error">Could not load this dataset. It may not exist.</Alert>
      </Container>
    );
  }

  return <WizardLayout dataset={data} />;
}
