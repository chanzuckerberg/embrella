'use client';

import { useState } from 'react';
import { Container, Paper, Typography } from '@mui/material';
import { useRouter } from 'next/navigation';
import { SessionForm } from './components/SessionForm';
import { SessionCreatedDialog } from './components/SessionCreatedDialog';
import { CreatedSession } from './types';

export default function CreateTEMSessionPage() {
  const router = useRouter();
  const [createdSession, setCreatedSession] = useState<CreatedSession | null>(null);

  return (
    <Container maxWidth="md" sx={{ py: 4 }}>
      <Paper sx={{ p: 4 }}>
        <Typography variant="h4" sx={{ fontWeight: 600, mb: 1 }}>
          Create TEM Session
        </Typography>
        <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
          Start a new transmission electron microscope data collection session.
        </Typography>
        <SessionForm onSuccess={(session) => setCreatedSession(session)} onCancel={() => router.back()} />
      </Paper>

      <SessionCreatedDialog
        open={createdSession !== null}
        session={createdSession}
        onCreateAnother={() => setCreatedSession(null)}
        onDone={() => router.push('/sessions/browse')}
      />
    </Container>
  );
}
