'use client';

import { Button, Icon } from '@czi-sds/components';
import { Box } from '@mui/material';

export function WizardFooter({
  disableBack,
  disableNext,
  savingNext = false,
  nextLabel = 'Next',
  readOnly = false,
  savingExit = false,
  onBack,
  onNext,
  onSaveAndExit,
}: {
  disableBack: boolean;
  disableNext: boolean;
  savingNext?: boolean;
  nextLabel?: string;
  readOnly?: boolean;
  savingExit?: boolean;
  onBack: () => void;
  onNext: () => void;
  onSaveAndExit: () => void;
}) {
  return (
    <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: '8px', justifyContent: 'space-between', alignItems: 'center' }}>
      <Button
        sdsType="secondary"
        sdsStyle="solid"
        startIcon={<Icon sdsIcon="ChevronLeft" sdsSize="xs" />}
        disabled={disableBack}
        onClick={onBack}
      >
        Back
      </Button>
      <Button sdsType="primary" sdsStyle="minimal" disabled={savingExit} onClick={onSaveAndExit}>
        {readOnly ? 'Close' : 'Save draft & exit'}
      </Button>
      <Button
        sdsType="primary"
        sdsStyle="solid"
        endIcon={savingNext ? undefined : <Icon sdsIcon="ChevronRight" sdsSize="xs" />}
        disabled={disableNext || savingNext}
        onClick={onNext}
      >
        {savingNext ? 'Saving…' : nextLabel}
      </Button>
    </Box>
  );
}
