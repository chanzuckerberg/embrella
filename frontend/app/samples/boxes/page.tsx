'use client';

import { Box, Container, Typography } from '@mui/material';
import { Button } from '@czi-sds/components';
import { DJANGO_URL } from '@app/common/constants/api';

export default function GridBoxesPage() {
  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      <Typography variant="h4" sx={{ fontWeight: 600, mb: 1 }}>
        Grid Boxes
      </Typography>
      <Typography variant="body1" color="text.secondary" sx={{ mb: 4 }}>
        View and manage the grid box hierarchy.
      </Typography>

      <Box sx={{ display: 'flex', gap: 2 }}>
        <Button
          sdsType="primary"
          sdsStyle="rounded"
          onClick={() => (window.location.href = `${DJANGO_URL}/cryo_grids/detail`)}
        >
          View Grid Box Hierarchy
        </Button>
      </Box>
    </Container>
  );
}
