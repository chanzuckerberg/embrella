'use client';

import { Container, Typography } from '@mui/material';

export default function ExportPage() {
  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      <Typography variant="h4" sx={{ color: '#6E4FF9', fontWeight: 600, mb: 1 }}>
        Data Export
      </Typography>
      <Typography variant="body1" color="text.secondary" sx={{ mb: 4 }}>
        Export functionality coming soon.
      </Typography>
    </Container>
  );
}
