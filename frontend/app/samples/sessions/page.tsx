'use client';

import { Box, Button, Paper, Typography } from '@mui/material';
import { DJANGO_URL } from '@app/common/constants/api';
import { PageContainer } from '@app/common/components/PageContainer';

export default function TEMSessionsPage() {
  return (
    <PageContainer>
      <Paper sx={{ p: 4 }}>
        <Typography variant="h4" gutterBottom color="primary">
          TEM Sessions
        </Typography>
        <Typography variant="body1" paragraph>
          Manage your transmission electron microscope data collection sessions.
        </Typography>

        <Box sx={{ mt: 4, display: 'flex', gap: 2, flexWrap: 'wrap' }}>
          <Button
            variant="contained"
            color="primary"
            onClick={() => (window.location.href = `${DJANGO_URL}/legacy/tem/reserve`)}
          >
            New Single-Grid TEM Session
          </Button>
          <Button
            variant="contained"
            color="primary"
            onClick={() => (window.location.href = `${DJANGO_URL}/legacy/tem/scrnreserve`)}
          >
            Screen Multiple Grids
          </Button>
          <Button
            variant="outlined"
            color="primary"
            onClick={() => (window.location.href = `${DJANGO_URL}/admin/tem/msisession/`)}
          >
            View All Sessions (Admin)
          </Button>
        </Box>

        <Box sx={{ mt: 4, p: 2, bgcolor: '#f3f0ff', borderRadius: 1 }}>
          <Typography variant="body2" color="text.secondary">
            <strong>Note:</strong> The TEM session management interface is currently hosted in Django. A fully
            integrated Next.js interface is planned for a future release.
          </Typography>
        </Box>
      </Paper>
    </PageContainer>
  );
}
