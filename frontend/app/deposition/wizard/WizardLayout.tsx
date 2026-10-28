'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Button, Icon } from '@czi-sds/components';
import { Alert, Box, Container, IconButton, Paper, Tooltip, Typography } from '@mui/material';

import { ConfirmDialog } from '@app/common/components/Forms/ConfirmDialog';
import type { Dataset } from '../types';
import { submissionPhases } from '../submitPhases';
import { usePreparationEditing } from '../hooks/usePreparationEditing';
import type { AutoSaveState } from '../hooks/useDraftAutoSave';
import { READ_ONLY_FIELDS_SX } from '../components/readOnlyStyles';
import { ReopenForEditing } from '../components/ReopenForEditing';
import { SaveIndicator } from './SaveIndicator';
import { WIZARD_STEPS } from './steps';
import { WizardFooter } from './WizardFooter';
import { WizardStepper } from './WizardStepper';

const SUBMISSIONS_HREF = '/deposition/submissions';

export function WizardLayout({ dataset }: { dataset: Dataset }) {
  const router = useRouter();
  const [confirmClose, setConfirmClose] = useState(false);
  const [current, setCurrent] = useState(1);
  const [save, setSave] = useState<AutoSaveState | null>(null);
  const [blocking, setBlocking] = useState(0);
  const [savingStep, setSavingStep] = useState<number | null>(null);
  const [closing, setClosing] = useState(false); // saving-and-exiting (distinct from per-step saves)
  const [manualAutofillSessions, setManualAutofillSessions] = useState<Set<string>>(() => new Set());
  const nonOwner = dataset.is_owner === false;
  const activeNums = WIZARD_STEPS.map((s) => s.num);
  const pos = activeNums.indexOf(current);
  const nextStep = WIZARD_STEPS.find((s) => s.num === activeNums[pos + 1]);
  const startsPreparation = !nonOwner && nextStep?.key === 'submit' && submissionPhases(dataset.job).sync === 'idle';

  const step = WIZARD_STEPS.find((s) => s.num === current) ?? WIZARD_STEPS[0];
  const Body = step.Component;
  const editing = usePreparationEditing(dataset);
  const readOnly = editing.readOnly;
  const lockedEdits = readOnly && !!save?.isDirty;
  const discardOnClose = readOnly || save?.status === 'error';
  const discardMessage = readOnly
    ? 'Your changes have not been saved. You can copy your values from this page before closing.'
    : 'Your changes have not been saved. Close without saving, or keep editing and choose Retry to try saving again.';
  // Save before leaving this step; abort on failure.
  const go = async (n: number) => {
    if (savingStep !== null || closing || lockedEdits || (n > current && blocking > 0)) return;
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
    if (savingStep !== null || closing) return;
    if (lockedEdits) {
      setConfirmClose(true);
      return;
    }
    setClosing(true);
    try {
      if (!readOnly && save && (await save.saveNow()) === false) return;
      setConfirmClose(false);
      router.push(SUBMISSIONS_HREF);
    } finally {
      setClosing(false);
    }
  };

  return (
    <Container maxWidth={false} sx={{ pt: 2, pb: 3, px: 3 }}>
      <Paper
        variant="outlined"
        sx={{
          ...READ_ONLY_FIELDS_SX,
          width: '100%',
          maxWidth: 1070,
          mx: 'auto',
          borderRadius: 3,
          display: 'flex',
          flexDirection: 'column',
          height: 'calc(100dvh - var(--wizard-top-offset, 130px) - 32px)',
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
                  <SaveIndicator
                    status={save.status}
                    isDirty={save.isDirty}
                    lastSavedAt={save.lastSavedAt}
                    onRetry={save.saveNow}
                  />
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
              <Tooltip title="Close">
                {/* span wrapper: Tooltip can't bind to a disabled button directly */}
                <span>
                  <IconButton
                    onClick={() => (save?.isDirty ? setConfirmClose(true) : saveAndExit())}
                    disabled={savingStep !== null || closing}
                    aria-label="Close wizard"
                  >
                    <Icon sdsIcon="XMark" sdsSize="l" />
                  </IconButton>
                </span>
              </Tooltip>
            </Box>
          </Box>
          <WizardStepper
            steps={WIZARD_STEPS}
            current={current}
            onSelect={go}
            disabled={lockedEdits || savingStep !== null || closing}
            blockForward={blocking > 0}
          />
        </Box>

        <Box
          sx={{
            flex: 1,
            minWidth: 0,
            minHeight: 0,
            overflowY: 'auto',
            overflowX: 'hidden',
            display: step.key === 'annotations' ? 'flex' : 'block',
            flexDirection: 'column',
            scrollbarGutter: 'stable',
            px: step.key === 'submit' ? { xs: '16px', md: '24px' } : { xs: 3, md: 5 },
            py: step.key === 'submit' ? { xs: '16px', lg: '24px' } : { xs: 4, md: 5 },
            '@media (max-height: 800px)': step.key === 'submit' ? { py: '12px' } : {},
            bgcolor: step.key === 'submit' ? 'grey.50' : 'background.paper',
          }}
        >
          {(step.key !== 'submit' || nonOwner) && <ReopenForEditing editing={editing} dataset={dataset} />}
          {lockedEdits && (
            <Alert severity="warning" sx={{ mb: 3 }}>
              You have unsaved changes. You can copy your values from this page before closing.
            </Alert>
          )}
          {save?.status === 'error' && save.error && (
            <Alert severity="error" sx={{ mb: 3 }}>
              {save.error}
            </Alert>
          )}
          <Body
            dataset={dataset}
            reportSave={setSave}
            reportBlocking={setBlocking}
            // Owners can upload while metadata is locked.
            readOnly={step.key === 'submit' ? nonOwner : readOnly}
            manualAutofillSessions={manualAutofillSessions}
            onManualAutofillEntry={(key) => setManualAutofillSessions((prev) => new Set(prev).add(key))}
          />
        </Box>

        <Box sx={{ flexShrink: 0, px: { xs: 3, md: 5 }, py: 2.5, borderTop: '1px solid', borderColor: 'divider' }}>
          <WizardFooter
            disableBack={pos <= 0 || savingStep !== null || closing || lockedEdits}
            disableNext={
              pos < 0 || pos >= activeNums.length - 1 || blocking > 0 || savingStep !== null || closing || lockedEdits
            }
            nextLabel={startsPreparation ? 'Next: prepare & validate' : 'Next'}
            savingNext={savingStep !== null && savingStep === activeNums[pos + 1]}
            onBack={() => pos > 0 && go(activeNums[pos - 1])}
            onNext={() => pos >= 0 && pos < activeNums.length - 1 && go(activeNums[pos + 1])}
            onSaveAndExit={saveAndExit}
            readOnly={readOnly}
            savingExit={closing}
          />
        </Box>
      </Paper>
      <ConfirmDialog
        open={confirmClose}
        onClose={() => !closing && setConfirmClose(false)}
        onConfirm={
          discardOnClose
            ? () => {
                save?.discardChanges();
                setConfirmClose(false);
                router.push(SUBMISSIONS_HREF);
              }
            : saveAndExit
        }
        title={discardOnClose ? 'Discard unsaved changes?' : 'Save changes before closing?'}
        heading="Unsaved changes"
        body={
          discardOnClose
            ? discardMessage
            : 'You have unsaved changes. Save your draft before leaving so you can return to it later.'
        }
        intent="warning"
        confirmText={discardOnClose ? 'Discard changes & close' : 'Save draft & close'}
        submittingText="Saving…"
        cancelText="Keep editing"
        isSubmitting={closing}
        error={save?.status === 'error' ? (save.error ?? 'Your changes could not be saved. Please try again.') : null}
      />
    </Container>
  );
}
