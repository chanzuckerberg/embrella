'use client';

import { useContext } from 'react';
import { Alert, AlertTitle, Box, Link, Typography } from '@mui/material';
import { FEATURE_FLAG, FeatureFlagsContext } from '@app/common/context/FeatureFlagsProvider';
import { DJANGO_URL } from '@app/common/constants/api';

// disclaimer for the public demo deployment
export const DemoBanner = () => {
  const featureFlags = useContext(FeatureFlagsContext);

  if (!featureFlags.includes(FEATURE_FLAG.DEMO)) {
    return null;
  }

  return (
    <Alert severity="info" sx={{ mb: 4 }}>
      <AlertTitle sx={{ fontWeight: 600 }}>You&apos;re trying out the Embrella demo</AlertTitle>
      <Box component="ul" sx={{ m: 0, pl: 2.5 }}>
        <Typography component="li" variant="body2">
          This server <strong>resets every day</strong>. Anything you create or edit here is reset.
        </Typography>
        <Typography component="li" variant="body2">
          Create and browse grids and sessions, open tomogram summaries and reviews, and walk through the job launch
          form.
        </Typography>
        <Typography component="li" variant="body2">
          <strong>Cluster access is turned off</strong>, so submitting jobs, live job status, and log fetching
          won&apos;t return results.
        </Typography>
      </Box>
      <Typography variant="body2" sx={{ mt: 1 }}>
        <Link href={`${DJANGO_URL}/docs/userguide/overview/`} target="_blank" rel="noopener">
          Read the user guide
        </Link>{' '}
        to see what Embrella does with a real cluster behind it.
      </Typography>
    </Alert>
  );
};
