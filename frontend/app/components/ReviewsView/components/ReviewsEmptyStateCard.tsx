import { Box, Typography } from '@mui/material';
import { Button, Icon } from '@czi-sds/components';
import Link from 'next/link';

export const ReviewsEmptyStateCard = () => {
  return (
    <Box sx={{ mt: 4, pl: 3 }}>
      <Box
        sx={{
          px: 4,
          py: 3.5,
          backgroundColor: 'grey.50',
          borderRadius: 1,
          display: 'inline-flex',
          alignItems: 'center',
          gap: 3,
        }}
      >
        <Icon sdsIcon="InfoCircle" sdsSize="l" color="gray" />
        <Box>
          <Typography variant="subtitle2">Don&apos;t see the review you&apos;re looking for?</Typography>
          <Typography variant="body2" color="text.secondary">
            Create a new review to get started.
          </Typography>
        </Box>
        <Link href="/processing/tomograms/reviews/create">
          <Button sdsType="secondary" sdsStyle="rounded">
            Create Review
          </Button>
        </Link>
      </Box>
    </Box>
  );
};
