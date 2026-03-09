'use client';

import { Container, Paper, Typography } from '@mui/material';
import { useRouter } from 'next/navigation';
import { SessionForm } from './components/SessionForm';

export default function CreateTEMSessionPage() {
  const router = useRouter();

  return (
    <Container maxWidth="md" sx={{ py: 4 }}>
      <Paper sx={{ p: 4 }}>
        <Typography variant="h4" sx={{ fontWeight: 600, mb: 1 }}>
          Create TEM Session
        </Typography>
        <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
          Start a new transmission electron microscope data collection session.
        </Typography>
        <SessionForm onSuccess={() => router.push('/sessions/browse')} onCancel={() => router.back()} />
      </Paper>
    </Container>
  );
}
