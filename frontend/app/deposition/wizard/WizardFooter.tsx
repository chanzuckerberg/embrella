'use client';

import NextLink from 'next/link';
import { Button } from '@czi-sds/components';
import ChevronLeftIcon from '@mui/icons-material/ChevronLeft';
import ChevronRightIcon from '@mui/icons-material/ChevronRight';
import { Box } from '@mui/material';

export function WizardFooter({
  disableBack,
  disableNext,
  onBack,
  onNext,
}: {
  disableBack: boolean;
  disableNext: boolean;
  onBack: () => void;
  onNext: () => void;
}) {
  return (
    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
      <Button sdsType="secondary" sdsStyle="solid" startIcon={<ChevronLeftIcon />} disabled={disableBack} onClick={onBack}>
        Back
      </Button>
      <Button component={NextLink} href="/deposition/submissions" sdsType="primary" sdsStyle="minimal">
        Save draft &amp; exit
      </Button>
      <Button sdsType="primary" sdsStyle="solid" endIcon={<ChevronRightIcon />} disabled={disableNext} onClick={onNext}>
        Next
      </Button>
    </Box>
  );
}
