'use client';

import { Box, Button, Paper, Typography } from '@mui/material';
import { DJANGO_URL } from '@app/common/constants/api';
import { PageContainer } from '@app/common/components/PageContainer';

export default function TEMSessionsListPage() {
  return (
    <PageContainer>
      <Paper sx={{ p: 4 }}>
        <Typography variant="h4" gutterBottom color="primary">
          TEM Session List
        </Typography>
        <Typography variant="body1" paragraph>
          Browse and search all transmission electron microscope sessions.
        </Typography>

        <Box sx={{ mt: 4, display: 'flex', gap: 2, flexWrap: 'wrap' }}>
          <Button
            variant="contained"
            color="primary"
            onClick={() => (window.location.href = `${DJANGO_URL}/admin/tem/msisession/`)}
          >
            View Single-Grid Sessions
          </Button>
          <Button
            variant="contained"
            color="primary"
            onClick={() => (window.location.href = `${DJANGO_URL}/tem/render_screening_form`)}
          >
            View Multi-Grid Screens
          </Button>
        </Box>

        <Box sx={{ mt: 4, p: 2, bgcolor: '#f3f0ff', borderRadius: 1 }}>
          <Typography variant="body2" color="text.secondary">
            <strong>Note:</strong> The TEM session list is currently hosted in Django Admin. A filterable table view
            similar to Grids and Tomograms is planned for a future release.
          </Typography>
        </Box>
      </Paper>
    </PageContainer>
  );
}
