'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import CloseIcon from '@mui/icons-material/Close';
import { Alert, Box, Container, IconButton, Paper, Tooltip, Typography } from '@mui/material';

import type { Dataset } from '../types';
import type { AutoSaveState } from '../hooks/useDraftAutoSave';
import { SaveIndicator } from './SaveIndicator';
import { WIZARD_STEPS, isStepSkipped } from './steps';
import { WizardFooter } from './WizardFooter';
import { WizardStepper } from './WizardStepper';

const SUBMISSIONS_HREF = '/deposition/submissions';

export function WizardLayout({ dataset }: { dataset: Dataset }) {
  const router = useRouter();
  const [current, setCurrent] = useState(1);
  const [save, setSave] = useState<AutoSaveState | null>(null);
  // Fail-open: read-only only when is_owner === false.
  const readOnly = dataset.is_owner === false;
  const skippedNums = WIZARD_STEPS.filter((s) => isStepSkipped(s, dataset)).map((s) => s.num);
  const activeNums = WIZARD_STEPS.filter((s) => !skippedNums.includes(s.num)).map((s) => s.num);
  const pos = activeNums.indexOf(current);

  const step = WIZARD_STEPS.find((s) => s.num === current) ?? WIZARD_STEPS[0];
  const Body = step.Component;
  // Step change "Next/Back button" unmounts the body; autosave flushes pending edits.
  const go = (n: number) => {
    setSave(null);
    setCurrent(n);
  };

  const saveAndExit = async () => {
    try {
      if (!readOnly) await save?.saveNow();
    } finally {
      router.push(SUBMISSIONS_HREF);
    }
  };

  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      <Paper variant="outlined" sx={{ borderRadius: 3 }}>
        <Box
          sx={{ px: { xs: 3, md: 5 }, pt: { xs: 3, md: 4 }, pb: 3, borderBottom: '1px solid', borderColor: 'divider' }}
        >
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 4 }}>
            <Box>
              <Typography variant="overline" sx={{ color: 'text.secondary', letterSpacing: 1.2, fontWeight: 600 }}>
                Step {step.num} of {WIZARD_STEPS.length}
              </Typography>
              <Typography variant="h4" sx={{ fontWeight: 700, lineHeight: 1.1 }}>
                {step.title}
              </Typography>
            </Box>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              {!readOnly && save && (
                <SaveIndicator status={save.status} lastSavedAt={save.lastSavedAt} onSaveNow={save.saveNow} />
              )}
              <Tooltip title="Close - your draft is saved">
                <IconButton onClick={saveAndExit} aria-label="Close wizard">
                  <CloseIcon />
                </IconButton>
              </Tooltip>
            </Box>
          </Box>
          <WizardStepper steps={WIZARD_STEPS} current={current} skipped={skippedNums} onSelect={go} />
        </Box>

        <Box sx={{ px: { xs: 3, md: 5 }, py: { xs: 4, md: 5 } }}>
          {readOnly && (
            <Alert severity="info" sx={{ mb: 3 }}>
              You&apos;re viewing another user&apos;s submission - it&apos;s read-only.
            </Alert>
          )}
          <Body dataset={dataset} reportSave={setSave} readOnly={readOnly} />
        </Box>

        <Box sx={{ px: { xs: 3, md: 5 }, py: 2.5, borderTop: '1px solid', borderColor: 'divider' }}>
          <WizardFooter
            disableBack={pos <= 0}
            disableNext={pos < 0 || pos >= activeNums.length - 1}
            onBack={() => pos > 0 && go(activeNums[pos - 1])}
            onNext={() => pos >= 0 && pos < activeNums.length - 1 && go(activeNums[pos + 1])}
            onSaveAndExit={saveAndExit}
          />
        </Box>
      </Paper>
    </Container>
  );
}
