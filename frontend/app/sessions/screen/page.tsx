'use client';

import { Box, Container, Typography } from '@mui/material';
import { Button } from '@czi-sds/components';
import { DJANGO_URL } from '@app/common/constants/api';

export default function ScreenMultipleGridsPage() {
  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      <Typography variant="h4" sx={{ fontWeight: 600, mb: 1 }}>
        Screen Multiple Grids
      </Typography>
      <Typography variant="body1" color="text.secondary" sx={{ mb: 4 }}>
        Set up a multi-grid screening session to evaluate multiple samples.
      </Typography>

      <Box sx={{ display: 'flex', gap: 2 }}>
        <Button
          sdsType="primary"
          sdsStyle="rounded"
          onClick={() => (window.location.href = `${DJANGO_URL}/legacy/tem/detail/`)}
        >
          Start Screening Session
        </Button>
      </Box>
    </Container>
  );
}
