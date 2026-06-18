'use client';

import { Box, Container, Typography } from '@mui/material';
import { Button, Icon } from '@czi-sds/components';
import { DJANGO_URL } from '@app/common/constants/api';

export default function BrowseSessionsPage() {
  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      <Typography variant="h4" sx={{ fontWeight: 600, mb: 1 }}>
        Browse TEM Sessions
      </Typography>
      <Typography variant="body1" color="text.secondary" sx={{ mb: 4 }}>
        Access and manage your TEM data collection sessions.
      </Typography>

      <Box sx={{ display: 'flex', gap: 2 }}>
        <Button
          sdsType="primary"
          sdsStyle="solid"
          onClick={() => (window.location.href = `${DJANGO_URL}/admin/tem/msisession/`)}
        >
          View Sessions
        </Button>
      </Box>

      <Box
        sx={{
          mt: 8,
          px: 3,
          py: 2.5,
          backgroundColor: 'grey.50',
          borderRadius: 1,
          display: 'inline-flex',
          alignItems: 'center',
          gap: 2.5,
        }}
      >
        <Icon sdsIcon="InfoCircle" sdsSize="l" color="gray" />
        <Box>
          <Typography variant="subtitle2">Looking for tomogram summaries?</Typography>
          <Typography variant="body2" color="text.secondary">
            Browse processed tomogram metadata across all sessions.
          </Typography>
        </Box>
        <Button
          sdsType="secondary"
          sdsStyle="outline"
          onClick={() => (window.location.href = '/processing/tomograms/metadata')}
        >
          Go to Tomogram Summaries
        </Button>
      </Box>
    </Container>
  );
}
