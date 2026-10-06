'use client';

import { Button } from '@czi-sds/components';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import ErrorIcon from '@mui/icons-material/Error';
import RadioButtonUncheckedIcon from '@mui/icons-material/RadioButtonUnchecked';
import {
  Alert,
  Box,
  Checkbox,
  CircularProgress,
  FormControlLabel,
  LinearProgress,
  Stack,
  Tooltip,
  Typography,
} from '@mui/material';

import type { JobState } from '../../types';
import type { StepProps } from '../wizardTypes';
import { useSubmitFlow } from '../../hooks/useSubmitFlow';

type PhaseStatus = 'idle' | 'active' | 'done' | 'error';

function syncStatus(state: JobState | undefined, hasPushId: boolean): PhaseStatus {
  if (!state || state === 'pending') return 'idle';
  if (state === 'prep_submitted' || state === 'prep_running') return 'active';
  if (state === 'failed' && !hasPushId) return 'error';
  return 'done';
}

function pushStatus(state: JobState | undefined, hasPushId: boolean): PhaseStatus {
  if (state === 'push_submitted' || state === 'push_running') return 'active';
  if (state === 'completed') return 'done';
  if (state === 'failed' && hasPushId) return 'error';
  return 'idle';
}

function focusPhase(sync: PhaseStatus, push: PhaseStatus): 1 | 2 | 3 {
  if (push !== 'idle') return 3;
  if (sync === 'done') return 2;
  return 1;
}

function prepLabel(pending: boolean, isError: boolean): string {
  if (pending) return 'Submitting…';
  if (isError) return 'Retry sync';
  return 'Submit for preparation';
}

function PhaseIcon({ status }: { status: PhaseStatus }) {
  if (status === 'active') return <CircularProgress size={18} />;
  if (status === 'done') return <CheckCircleIcon sx={{ color: 'success.main' }} fontSize="small" />;
  if (status === 'error') return <ErrorIcon sx={{ color: 'error.main' }} fontSize="small" />;
  return <RadioButtonUncheckedIcon sx={{ color: 'text.disabled' }} fontSize="small" />;
}

function PhaseTile({
  n,
  title,
  sub,
  status,
  active,
}: {
  n: number;
  title: string;
  sub: string;
  status: PhaseStatus;
  active: boolean;
}) {
  return (
    <Box
      sx={{
        flex: 1,
        p: 2,
        display: 'flex',
        gap: 1.5,
        alignItems: 'flex-start',
        borderBottom: '2px solid',
        borderColor: active ? 'primary.main' : 'transparent',
      }}
    >
      <PhaseIcon status={status} />
      <Box>
        <Typography variant="body2" sx={{ fontWeight: 700 }}>
          {n} · {title}
        </Typography>
        <Typography variant="caption" color="text.secondary">
          {sub}
        </Typography>
      </Box>
    </Box>
  );
}

function LiveLog({ text }: { text?: string | null }) {
  const lines = (text ?? '').split('\n').filter(Boolean);
  const copy = () => {
    if (text && navigator.clipboard) navigator.clipboard.writeText(text).catch(() => undefined);
  };
  return (
    <Box sx={{ bgcolor: 'grey.900', borderRadius: 2, p: 2, minHeight: 220, display: 'flex', flexDirection: 'column' }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
        <Typography variant="body2" sx={{ color: 'grey.100', fontWeight: 700 }}>
          Live log (tail)
        </Typography>
        <Button sdsType="secondary" sdsStyle="minimal" size="small" onClick={copy} disabled={!lines.length}>
          Copy
        </Button>
      </Box>
      <Box sx={{ fontFamily: 'monospace', fontSize: 12, color: 'grey.300', whiteSpace: 'pre-wrap' }}>
        {lines.length ? (
          lines.map((line, i) => <div key={i}>{line}</div>)
        ) : (
          <Typography variant="caption" sx={{ color: 'grey.500' }}>
            Live log streaming isn&apos;t available yet — it will appear here once the backend streams it.
          </Typography>
        )}
      </Box>
    </Box>
  );
}

export function SubmitStep({ dataset: initial, readOnly }: StepProps) {
  const { dataset, submit, push } = useSubmitFlow(initial);
  const state = dataset.job?.state;
  const hasPushId = !!dataset.job?.push_slurm_job_id;

  const sync = syncStatus(state, hasPushId);
  const pushed = pushStatus(state, hasPushId);
  const focus = focusPhase(sync, pushed);

  const actionError = (submit.error as Error | null)?.message || (push.error as Error | null)?.message;
  const errorMessage = dataset.job?.error_message;

  return (
    <Stack spacing={3}>
      {/* Phase sub-stepper */}
      <Box sx={{ display: 'flex', border: '1px solid', borderColor: 'divider', borderRadius: 2, overflow: 'hidden' }}>
        <PhaseTile
          n={1}
          title="Sync on cluster"
          status={sync}
          active={focus === 1}
          sub={{ idle: 'Not started', active: 'In progress', done: 'Complete', error: 'Failed' }[sync]}
        />
        <PhaseTile n={2} title="Pre-flight validation" status="idle" active={focus === 2} sub="Not available yet" />
        <PhaseTile
          n={3}
          title="Push to S3"
          status={pushed}
          active={focus === 3}
          sub={{ idle: 'Waiting on submit', active: 'Uploading…', done: 'Complete', error: 'Failed' }[pushed]}
        />
      </Box>

      <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: '1fr 1fr' }, gap: 3 }}>
        {/* Left: phase detail + actions */}
        <Stack spacing={2}>
          {focus === 1 && (
            <Box sx={{ border: '1px solid', borderColor: 'divider', borderRadius: 2, p: 2 }}>
              <Typography variant="subtitle2" sx={{ fontWeight: 700, mb: 1 }}>
                Local sync on cluster
              </Typography>
              <Typography variant="caption" sx={{ fontFamily: 'monospace', color: 'text.secondary' }}>
                cryoetportalprep sync ./dataprep_config.yaml
              </Typography>
              {sync === 'active' && <LinearProgress sx={{ mt: 2 }} />}
              <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 1.5 }}>
                Per-object progress and the symlink/deposit breakdown aren&apos;t available yet.
              </Typography>
            </Box>
          )}

          {focus === 2 && (
            <Box sx={{ border: '1px solid', borderColor: 'divider', borderRadius: 2, p: 2 }}>
              <Typography variant="subtitle2" sx={{ fontWeight: 700, mb: 1 }}>
                Pre-flight validation
              </Typography>
              <Alert severity="info" sx={{ mb: 2 }}>
                Pre-flight validation runs on the cluster — not wired up yet. You can submit for upload.
              </Alert>
            </Box>
          )}

          {focus === 3 && (
            <Box sx={{ border: '1px solid', borderColor: 'divider', borderRadius: 2, p: 2 }}>
              <Typography variant="subtitle2" sx={{ fontWeight: 700, mb: 1 }}>
                {pushed === 'done' ? 'Pushed to the data portal' : 'Pushing to S3'}
              </Typography>
              {pushed === 'active' && <LinearProgress sx={{ my: 1 }} />}
              {dataset.job?.push_slurm_job_id && (
                <Typography variant="caption" color="text.secondary">
                  SLURM job {dataset.job.push_slurm_job_id}
                </Typography>
              )}
              <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 1 }}>
                Upload byte-progress isn&apos;t available yet.
              </Typography>
            </Box>
          )}

          {state === 'failed' && (
            <Alert severity="error">{errorMessage || 'Submission failed. You can try again.'}</Alert>
          )}
          {pushed === 'done' && <Alert severity="success">Submitted — uploaded to the data portal.</Alert>}
          {actionError && <Alert severity="error">{actionError}</Alert>}

          {!readOnly && (
            <Box sx={{ display: 'flex', gap: 2 }}>
              {(sync === 'idle' || sync === 'error') && (
                <Button sdsType="primary" sdsStyle="solid" disabled={submit.isPending} onClick={() => submit.mutate()}>
                  {prepLabel(submit.isPending, sync === 'error')}
                </Button>
              )}
              {focus === 2 && (
                <Button sdsType="primary" sdsStyle="solid" disabled={push.isPending} onClick={() => push.mutate()}>
                  {push.isPending ? 'Submitting…' : 'Submit deposition'}
                </Button>
              )}
            </Box>
          )}
        </Stack>

        {/* Right: live log */}
        <Stack spacing={2}>
          <LiveLog text={null} />
          <Tooltip title="Email notifications aren't wired up yet.">
            <FormControlLabel
              control={<Checkbox checked disabled />}
              label={
                <Box>
                  <Typography variant="body2">Email me when this finishes</Typography>
                  <Typography variant="caption" color="text.secondary">
                    You can close this tab — sync and push keep running.
                  </Typography>
                </Box>
              }
            />
          </Tooltip>
        </Stack>
      </Box>
    </Stack>
  );
}
