import { Box, Container, Typography } from '@mui/material';
import type { Metadata } from 'next';

export const metadata: Metadata = { title: 'New Submission' };

export default function NewSubmissionPage() {
  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      <Typography variant="h4" sx={{ fontWeight: 600, mb: 1 }}>
        New Submission
      </Typography>
      <Typography variant="body1" color="text.secondary" sx={{ mb: 4 }}>
        Start a new deposition to the cryo-ET data portal.
      </Typography>

      <Box sx={{ color: 'text.secondary' }}>Coming soon.</Box>
    </Container>
  );
}
