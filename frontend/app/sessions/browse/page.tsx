'use client';

import { Box, Container, Typography } from '@mui/material';
import { Button, Icon } from '@czi-sds/components';

export default function BrowseSessionsPage() {
  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      <Typography variant="h4" sx={{ fontWeight: 600, mb: 1 }}>
        Browse TEM Sessions
      </Typography>
      <Typography variant="body1" color="text.secondary">
        A full session browser is on the way. In the meantime, tomogram summaries cover session-level processing
        results.
      </Typography>

      <Box
        sx={{
          mt: 4,
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
