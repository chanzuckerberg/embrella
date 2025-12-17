'use client';

import { Box, Container, Typography } from '@mui/material';
import { Button } from '@czi-sds/components';
import { DJANGO_URL } from '@app/common/constants/api';

export default function NewTEMSessionPage() {
  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      <Typography variant="h4" sx={{ fontWeight: 600, mb: 1 }}>
        Create New TEM Session
      </Typography>
      <Typography variant="body1" color="text.secondary" sx={{ mb: 4 }}>
        Start a new transmission electron microscope data collection session.
      </Typography>

      <Box sx={{ display: 'flex', gap: 2 }}>
        <Button
          sdsType="primary"
          sdsStyle="rounded"
          onClick={() => (window.location.href = `${DJANGO_URL}/tem/reserve`)}
        >
          Start Single-Grid Session
        </Button>
      </Box>
    </Container>
  );
}
