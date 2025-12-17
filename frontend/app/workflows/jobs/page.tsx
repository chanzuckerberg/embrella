'use client';

import { Box, Button, Paper, Typography } from '@mui/material';
import { DJANGO_URL } from '@app/common/constants/api';
import { PageContainer } from '@app/common/components/PageContainer';

export default function WorkflowJobsPage() {
  return (
    <PageContainer>
      <Paper sx={{ p: 4 }}>
        <Typography variant="h4" gutterBottom color="primary">
          Job History & Logs
        </Typography>
        <Typography variant="body1" paragraph>
          View detailed logs and history for all workflow jobs.
        </Typography>

        <Box sx={{ mt: 4, display: 'flex', gap: 2, flexWrap: 'wrap' }}>
          <Button
            variant="contained"
            color="primary"
            onClick={() => (window.location.href = `${DJANGO_URL}/workflow/logs`)}
          >
            View Job Logs
          </Button>
          <Button
            variant="outlined"
            color="primary"
            onClick={() => (window.location.href = `${DJANGO_URL}/workflow/dashboard`)}
          >
            Back to Dashboard
          </Button>
        </Box>

        <Box sx={{ mt: 4, p: 2, bgcolor: '#f3f0ff', borderRadius: 1 }}>
          <Typography variant="body2" color="text.secondary">
            <strong>Note:</strong> Job logs and history are currently viewed through the Django interface. A dedicated
            Next.js log viewer is planned for a future release.
          </Typography>
        </Box>
      </Paper>
    </PageContainer>
  );
}
