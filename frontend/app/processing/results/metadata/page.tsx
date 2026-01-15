'use client';

import { Box, Paper, Typography } from '@mui/material';
import { PageContainer } from '@app/common/components/PageContainer';

export default function ResultsMetadataPage() {
  return (
    <PageContainer>
      <Paper sx={{ p: 4 }}>
        <Typography variant="h4" gutterBottom color="primary">
          Processing Results Metadata
        </Typography>
        <Typography variant="body1" paragraph>
          View detailed metadata visualizations for processing runs and TEM sessions.
        </Typography>

        <Box sx={{ mt: 4, p: 2, bgcolor: '#f3f0ff', borderRadius: 1 }}>
          <Typography variant="body2" color="text.secondary">
            <strong>How to access:</strong> Metadata visualizations are accessible from the TEM session list and
            processing run details pages. Navigate to a specific session or run using the dynamic route pattern:{' '}
            <code>/metadata/view/[session]/[run]</code>
          </Typography>
        </Box>

        <Box sx={{ mt: 2, p: 2, bgcolor: '#f3e5f5', borderRadius: 1 }}>
          <Typography variant="body2" color="text.secondary">
            <strong>Features:</strong> The metadata viewer provides interactive charts and graphs for analyzing data
            quality, collection parameters, alignment metrics, and processing statistics.
          </Typography>
        </Box>
      </Paper>
    </PageContainer>
  );
}
