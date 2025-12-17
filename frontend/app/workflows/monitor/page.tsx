'use client';

import { Box, Button, Paper, Typography } from '@mui/material';
import { DJANGO_URL } from '@app/common/constants/api';
import { PageContainer } from '@app/common/components/PageContainer';

export default function WorkflowMonitorPage() {
  return (
    <PageContainer>
      <Paper sx={{ p: 4 }}>
        <Typography variant="h4" gutterBottom color="primary">
          Workflow Monitor
        </Typography>
        <Typography variant="body1" paragraph>
          Monitor active workflows and view real-time job status.
        </Typography>

        <Box sx={{ mt: 4, display: 'flex', gap: 2, flexWrap: 'wrap' }}>
          <Button
            variant="contained"
            color="primary"
            onClick={() => (window.location.href = `${DJANGO_URL}/workflow/dashboard`)}
          >
            Workflow Dashboard
          </Button>
          <Button
            variant="contained"
            color="primary"
            onClick={() => (window.location.href = `${DJANGO_URL}/workflow/track`)}
          >
            Track Active Jobs
          </Button>
          <Button
            variant="outlined"
            color="error"
            onClick={() => (window.location.href = `${DJANGO_URL}/workflow/cancel`)}
          >
            Cancel Jobs
          </Button>
        </Box>

        <Box sx={{ mt: 4, p: 2, bgcolor: '#f3f0ff', borderRadius: 1 }}>
          <Typography variant="body2" color="text.secondary">
            <strong>Note:</strong> The workflow monitoring dashboard is currently hosted in Django. It provides
            real-time status updates and job control functionality.
          </Typography>
        </Box>
      </Paper>
    </PageContainer>
  );
}
