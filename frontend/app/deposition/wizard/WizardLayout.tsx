'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Button, Icon } from '@czi-sds/components';
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
  const [blocking, setBlocking] = useState(0);
  const [savingStep, setSavingStep] = useState<number | null>(null);
  const [manualAutofillSessions, setManualAutofillSessions] = useState<Set<string>>(() => new Set());
  const readOnly = dataset.is_owner === false;
  const skippedNums = WIZARD_STEPS.filter((s) => isStepSkipped(s, dataset)).map((s) => s.num);
  const activeNums = WIZARD_STEPS.filter((s) => !skippedNums.includes(s.num)).map((s) => s.num);
  const pos = activeNums.indexOf(current);

  const step = WIZARD_STEPS.find((s) => s.num === current) ?? WIZARD_STEPS[0];
  const Body = step.Component;
  // Save before leaving this step; abort on failure.
  const go = async (n: number) => {
    if (savingStep !== null) return;
    setSavingStep(n);
    try {
      if (!readOnly && save && (await save.saveNow()) === false) return;
      setSave(null);
      setBlocking(0);
      setCurrent(n);
    } finally {
      setSavingStep(null);
    }
  };

  const saveAndExit = async () => {
    if (savingStep !== null) return;
    if (!readOnly && save && (await save.saveNow()) === false) return;
    router.push(SUBMISSIONS_HREF);
  };

  return (
    <Container maxWidth={false} sx={{ pt: 2, pb: 3, px: 3 }}>
      <Paper
        variant="outlined"
        sx={{
          width: '100%',
          maxWidth: 1070,
          mx: 'auto',
          borderRadius: 3,
          display: 'flex',
          flexDirection: 'column',
          height: 'calc(100vh - 174px)',
          overflow: 'hidden',
        }}
      >
        <Box
          sx={{
            flexShrink: 0,
            px: { xs: 3, md: 5 },
            pt: { xs: 2, md: 0.5 },
            pb: 3,
            borderBottom: '1px solid',
            borderColor: 'divider',
          }}
        >
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 0.5 }}>
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
                <>
                  <SaveIndicator status={save.status} lastSavedAt={save.lastSavedAt} onRetry={save.saveNow} />
                  <Button
                    sdsType="secondary"
                    sdsStyle="outline"
                    size="small"
                    disabled={save.status === 'saving'}
                    onClick={save.saveNow}
                  >
                    Save now
                  </Button>
                </>
              )}
              <Tooltip title={readOnly ? 'Close wizard' : 'Save draft and close'}>
                <IconButton onClick={saveAndExit} aria-label="Close wizard">
                  <Icon sdsIcon="XMark" sdsSize="l" />
                </IconButton>
              </Tooltip>
            </Box>
          </Box>
          <WizardStepper steps={WIZARD_STEPS} current={current} skipped={skippedNums} onSelect={go} />
        </Box>

        <Box
          sx={{
            flex: 1,
            minHeight: 0,
            overflowY: 'auto',
            display: step.key === 'annotations' ? 'flex' : 'block',
            flexDirection: 'column',
            scrollbarGutter: 'stable',
            px: { xs: 3, md: 5 },
            py: { xs: 4, md: 5 },
          }}
        >
          {readOnly && (
            <Alert severity="info" sx={{ mb: 3 }}>
              You&apos;re viewing another user&apos;s submission - it&apos;s read-only.
            </Alert>
          )}
          <Body
            dataset={dataset}
            reportSave={setSave}
            reportBlocking={setBlocking}
            readOnly={readOnly}
            manualAutofillSessions={manualAutofillSessions}
            onManualAutofillEntry={(key) => setManualAutofillSessions((prev) => new Set(prev).add(key))}
          />
        </Box>

        <Box sx={{ flexShrink: 0, px: { xs: 3, md: 5 }, py: 2.5, borderTop: '1px solid', borderColor: 'divider' }}>
          <WizardFooter
            disableBack={pos <= 0 || savingStep !== null}
            disableNext={pos < 0 || pos >= activeNums.length - 1 || blocking > 0 || savingStep !== null}
            savingNext={savingStep !== null && savingStep === activeNums[pos + 1]}
            onBack={() => pos > 0 && go(activeNums[pos - 1])}
            onNext={() => pos >= 0 && pos < activeNums.length - 1 && go(activeNums[pos + 1])}
            onSaveAndExit={saveAndExit}
          />
        </Box>
      </Paper>
    </Container>
  );
}
