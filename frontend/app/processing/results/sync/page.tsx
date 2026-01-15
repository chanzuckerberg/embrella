'use client';

import { Box, Button, Paper, Typography } from '@mui/material';
import { DJANGO_URL } from '@app/common/constants/api';
import { PageContainer } from '@app/common/components/PageContainer';

export default function ResultsSyncPage() {
  return (
    <PageContainer>
      <Paper sx={{ p: 4 }}>
        <Typography variant="h4" gutterBottom color="primary">
          Synchronize Processing Results
        </Typography>
        <Typography variant="body1" paragraph>
          Synchronize tomogram data between remote storage and local systems.
        </Typography>

        <Box sx={{ mt: 4 }}>
          <Button
            variant="contained"
            color="primary"
            size="large"
            onClick={() => (window.location.href = `${DJANGO_URL}/processes/sync_tomograms`)}
          >
            Sync Tomograms
          </Button>
        </Box>

        <Box sx={{ mt: 4, p: 2, bgcolor: '#fff3e0', borderRadius: 1 }}>
          <Typography variant="body2" color="text.secondary">
            <strong>Warning:</strong> Data synchronization operations may take a long time to complete and require
            significant network bandwidth. Monitor the progress through the workflow dashboard.
          </Typography>
        </Box>

        <Box sx={{ mt: 2, p: 2, bgcolor: '#f3f0ff', borderRadius: 1 }}>
          <Typography variant="body2" color="text.secondary">
            <strong>Note:</strong> The synchronization interface is currently hosted in Django. Track sync progress from
            the Processing → Monitor dashboard.
          </Typography>
        </Box>
      </Paper>
    </PageContainer>
  );
}
