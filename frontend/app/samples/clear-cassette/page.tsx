'use client';

import { Box, Container, Typography } from '@mui/material';
import { Button } from '@czi-sds/components';
import { DJANGO_URL } from '@app/common/constants/api';

export default function ClearCassettePage() {
  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      <Typography variant="h4" sx={{ fontWeight: 600, mb: 1 }}>
        Clear Cassette
      </Typography>
      <Typography variant="body1" color="text.secondary" sx={{ mb: 4 }}>
        Remove grids from a cassette and update their storage locations.
      </Typography>

      <Box sx={{ display: 'flex', gap: 2 }}>
        <Button
          sdsType="primary"
          sdsStyle="rounded"
          onClick={() => (window.location.href = `${DJANGO_URL}/cryo_grids/clear_cassette`)}
        >
          Clear a Cassette
        </Button>
      </Box>
    </Container>
  );
}
