'use client';

import { useEffect, useRef, useState } from 'react';
import { Button, Icon } from '@czi-sds/components';
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

import type {
  JobState,
  JobValidation,
  SyncChecklistItem,
  SyncProgress,
  SyncSummary,
  ValidationWarning,
} from '../../types';
import type { StepProps } from '../wizardTypes';
import { useSubmitFlow } from '../../hooks/useSubmitFlow';
import { checkSshSetup, isSshSetupRequired } from '../../services/depositionApi';
import { SSHSetupModal } from '@app/common/components/SSHSetupModal';

type PhaseStatus = 'idle' | 'active' | 'done' | 'warning' | 'error';
type SubmitPhase = 'prep' | 'push';

const DEFAULT_SYNC_COMMAND = 'cryoetportalprep sync ./dataprep_config.yaml';
const DEFAULT_PUSH_COMMAND = 'aws s3 sync <staged dir> <s3 bucket> --follow-symlinks';

function syncStatus(state: JobState | undefined, hasPushId: boolean): PhaseStatus {
  if (!state || state === 'pending') return 'idle';
  if (state === 'prep_submitted' || state === 'prep_running') return 'active';
  if (state === 'failed' && !hasPushId) return 'error';
  return 'done';
}

function validationStatus(validation: JobValidation | null | undefined): PhaseStatus {
  if (!validation) return 'idle';
  if (!validation.passed) return 'error';
  return validation.warnings.length ? 'warning' : 'done';
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

function toPct(done: number, total: number): number {
  return total > 0 ? Math.round((done / total) * 100) : 0;
}

function pluralWarnings(n: number): string {
  return `${n} warning${n === 1 ? '' : 's'}`;
}

function syncSub(status: PhaseStatus, progress?: SyncProgress | null, summary?: SyncSummary | null): string {
  if (status === 'active') {
    if (!progress) return 'In progress';
    const base = `${toPct(progress.done, progress.total)}%`;
    return progress.eta ? `${base} · ETA ${progress.eta}` : base;
  }
  if (status === 'done') return summary ? `Complete · ${summary.objects.toLocaleString()} objects` : 'Complete';
  if (status === 'error') return 'Failed';
  return 'Not started';
}

function validationSub(status: PhaseStatus, validation?: JobValidation | null): string {
  if (status === 'warning' && validation) return `Passed · ${pluralWarnings(validation.warnings.length)}`;
  if (status === 'done') return 'Passed';
  if (status === 'error') return 'Issues found';
  return 'Not available yet';
}

function validationSeverity(validation: JobValidation): 'success' | 'warning' | 'error' {
  if (!validation.passed) return 'error';
  return validation.warnings.length ? 'warning' : 'success';
}

function validationTitle(validation: JobValidation): string {
  if (!validation.passed) return 'Validation found blocking issues';
  return validation.warnings.length
    ? `Validation passed with ${pluralWarnings(validation.warnings.length)}`
    : 'Validation passed';
}

function validationBody(validation: JobValidation): string {
  if (!validation.passed) return 'These issues must be resolved before the deposition can be pushed.';
  return validation.warnings.length ? 'You can submit — review the warnings below before you do.' : 'You can submit.';
}

const PUSH_SUB: Record<PhaseStatus, string> = {
  idle: 'Waiting on submit',
  active: 'Uploading…',
  done: 'Complete',
  warning: 'Uploading…',
  error: 'Failed',
};

function pushHeading(status: PhaseStatus): string {
  if (status === 'done') return 'Pushed to the data portal';
  if (status === 'error') return 'Push failed';
  return 'Pushing to S3';
}

function summaryLine(s: SyncSummary): string {
  return [`${s.objects.toLocaleString()} objects`, s.size, s.duration].filter(Boolean).join(' · ');
}

function EmptyCircle({ color = 'text.disabled' }: { color?: string }) {
  return <Box sx={{ width: 16, height: 16, borderRadius: '50%', border: '2px solid', borderColor: color }} />;
}

function PhaseIcon({ status }: { status: PhaseStatus }) {
  if (status === 'active') return <CircularProgress size={18} />;
  if (status === 'done') return <Icon sdsIcon="CheckCircle" sdsSize="s" color="green" />;
  if (status === 'warning') return <Icon sdsIcon="ExclamationMarkCircle" sdsSize="s" color="yellow" />;
  if (status === 'error') return <Icon sdsIcon="ExclamationMarkCircle" sdsSize="s" color="red" />;
  return <EmptyCircle />;
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

function CommandBox({ text }: { text: string }) {
  return (
    <Box sx={{ bgcolor: 'grey.100', border: '1px solid', borderColor: 'divider', borderRadius: 1, p: 1.5 }}>
      <Typography variant="caption" noWrap sx={{ fontFamily: 'monospace', display: 'block' }}>
        {text}
      </Typography>
    </Box>
  );
}

function SyncChecklist({ items }: { items: SyncChecklistItem[] }) {
  return (
    <Stack spacing={1} sx={{ mt: 2 }}>
      {items.map((it) => {
        const complete = it.total > 0 && it.done >= it.total;
        return (
          <Box key={it.label} sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              {complete ? (
                <Icon sdsIcon="CheckCircle" sdsSize="s" color="green" />
              ) : (
                <EmptyCircle color="primary.main" />
              )}
              <Typography variant="body2">{it.label}</Typography>
            </Box>
            <Typography variant="body2" sx={{ color: complete ? 'success.main' : 'primary.main' }}>
              {it.done.toLocaleString()} / {it.total.toLocaleString()}
            </Typography>
          </Box>
        );
      })}
    </Stack>
  );
}

function WarningsList({ warnings, blocking }: { warnings: ValidationWarning[]; blocking?: boolean }) {
  return (
    <Box sx={{ border: '1px solid', borderColor: 'divider', borderRadius: 2, mt: 2 }}>
      {warnings.map((w, i) => (
        <Box
          key={`${w.message}-${i}`}
          sx={{ display: 'flex', gap: 1.5, p: 2, borderTop: i ? '1px solid' : 'none', borderColor: 'divider' }}
        >
          <Icon sdsIcon="ExclamationMarkCircle" sdsSize="s" color={blocking ? 'red' : 'yellow'} />
          <Box>
            <Typography variant="body2">{w.message}</Typography>
            {w.path && (
              <Typography variant="caption" sx={{ fontFamily: 'monospace', color: 'text.secondary' }}>
                {w.path}
              </Typography>
            )}
          </Box>
        </Box>
      ))}
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
            Live log streaming isn&apos;t available yet - it will appear here once the backend streams it.
          </Typography>
        )}
      </Box>
    </Box>
  );
}

export function SubmitStep({ dataset: initial, readOnly }: StepProps) {
  const { dataset, submit, push } = useSubmitFlow(initial);
  const [showPreview, setShowPreview] = useState(false);
  const [ssh, setSsh] = useState<{ cluster: string; username: string; phase: SubmitPhase } | null>(null);
  const started = useRef(false);

  const job = dataset.job;
  const state = job?.state;
  const hasPushId = !!job?.push_slurm_job_id;

  const sync = syncStatus(state, hasPushId);

  const openSshIfNeeded = (err: unknown, phase: SubmitPhase) => {
    if (!isSshSetupRequired(err)) return;
    const cluster = err.clusterId;
    checkSshSetup(cluster)
      .then(({ username }) => setSsh({ cluster, username, phase }))
      .catch(() => setSsh({ cluster, username: '', phase }));
  };

  const runSync = () => {
    submit.reset();
    submit.mutate(undefined, { onError: (e) => openSshIfNeeded(e, 'prep') });
  };
  const runPush = () => {
    push.reset();
    push.mutate(undefined, { onError: (e) => openSshIfNeeded(e, 'push') });
  };

  // Landing on this step kicks off the sync — no manual start button (matches the mock).
  useEffect(() => {
    if (!readOnly && sync === 'idle' && !submit.isPending && !started.current) {
      started.current = true;
      runSync();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- fire once on first idle render
  }, [readOnly, sync]);

  const validation = validationStatus(job?.validation);
  const pushed = pushStatus(state, hasPushId);
  const focus = focusPhase(sync, pushed);

  const progress = job?.sync_progress ?? null;
  const summary = job?.sync_summary ?? null;
  const warnings = job?.validation?.warnings ?? [];
  const canPush = !job?.validation || job.validation.passed;

  const submitError = isSshSetupRequired(submit.error) ? null : (submit.error as Error | null)?.message;
  const pushError = isSshSetupRequired(push.error) ? null : (push.error as Error | null)?.message;
  const actionError = submitError || pushError;
  const errorMessage = job?.error_message;

  const sessionCount = dataset.session_count ?? dataset.sessions?.length ?? 0;
  const datasetLabel = dataset.dataset_id ? `${dataset.title} (#${dataset.dataset_id})` : dataset.title;

  return (
    <Stack spacing={3}>
      {/* Review summary */}
      <Box>
        <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>
          {datasetLabel}
        </Typography>
        <Typography variant="body2" color="text.secondary">
          {sessionCount} imaging session{sessionCount === 1 ? '' : 's'}
        </Typography>
      </Box>

      {/* Phase sub-stepper */}
      <Box sx={{ display: 'flex', border: '1px solid', borderColor: 'divider', borderRadius: 2, overflow: 'hidden' }}>
        <PhaseTile
          n={1}
          title="Sync on cluster"
          status={sync}
          active={focus === 1}
          sub={syncSub(sync, progress, summary)}
        />
        <PhaseTile
          n={2}
          title="Pre-flight validation"
          status={validation}
          active={focus === 2}
          sub={validationSub(validation, job?.validation)}
        />
        <PhaseTile n={3} title="Push to S3" status={pushed} active={focus === 3} sub={PUSH_SUB[pushed]} />
      </Box>

      <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: '1fr 1fr' }, gap: 3 }}>
        {/* Left: phase detail + actions */}
        <Stack spacing={2}>
          {focus === 1 && (
            <Box sx={{ border: '1px solid', borderColor: 'divider', borderRadius: 2, p: 2 }}>
              <Typography variant="subtitle2" sx={{ fontWeight: 700, mb: 1.5 }}>
                Local sync on cluster
              </Typography>
              <CommandBox text={job?.sync_command ?? DEFAULT_SYNC_COMMAND} />
              {progress ? (
                <>
                  <LinearProgress variant="determinate" value={toPct(progress.done, progress.total)} sx={{ mt: 2 }} />
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', mt: 1 }}>
                    <Typography variant="caption" color="text.secondary">
                      {progress.done.toLocaleString()} / {progress.total.toLocaleString()} objects
                    </Typography>
                    <Typography variant="caption" sx={{ color: 'primary.main', fontWeight: 700 }}>
                      {toPct(progress.done, progress.total)}%{progress.eta ? ` · ETA ${progress.eta}` : ''}
                    </Typography>
                  </Box>
                  {progress.items && progress.items.length > 0 && <SyncChecklist items={progress.items} />}
                </>
              ) : (
                <>
                  {sync === 'active' && <LinearProgress sx={{ mt: 2 }} />}
                  <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 1.5 }}>
                    Per-object progress and the symlink/deposit breakdown aren&apos;t available yet.
                  </Typography>
                </>
              )}
              {!readOnly && (sync === 'error' || submit.isError) && (
                <Box sx={{ mt: 2 }}>
                  <Button sdsType="primary" sdsStyle="solid" disabled={submit.isPending} onClick={runSync}>
                    {submit.isPending ? 'Retrying…' : 'Retry sync'}
                  </Button>
                </Box>
              )}
            </Box>
          )}

          {focus === 2 && (
            <Box sx={{ border: '1px solid', borderColor: 'divider', borderRadius: 2, p: 2 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <Icon sdsIcon="CheckCircle" sdsSize="s" color="green" />
                <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>
                  Local sync complete
                </Typography>
                {summary && (
                  <Typography variant="caption" color="text.secondary">
                    {summaryLine(summary)}
                  </Typography>
                )}
              </Box>

              <Typography variant="subtitle2" sx={{ fontWeight: 700, mt: 2.5, mb: 1 }}>
                Pre-flight validation
              </Typography>
              {job?.validation ? (
                <>
                  <Alert severity={validationSeverity(job.validation)}>
                    <Typography variant="body2" sx={{ fontWeight: 700 }}>
                      {validationTitle(job.validation)}
                    </Typography>
                    <Typography variant="body2">{validationBody(job.validation)}</Typography>
                  </Alert>
                  {warnings.length > 0 && <WarningsList warnings={warnings} blocking={!job.validation.passed} />}
                </>
              ) : (
                <Alert severity="info">
                  Pre-flight validation runs on the cluster — not wired up yet. You can submit for upload.
                </Alert>
              )}

              {!readOnly && (
                <Box sx={{ display: 'flex', gap: 2, mt: 2.5 }}>
                  <Button sdsType="primary" sdsStyle="solid" disabled={push.isPending || !canPush} onClick={runPush}>
                    {push.isPending ? 'Submitting…' : 'Submit deposition'}
                  </Button>
                  <Button sdsType="secondary" sdsStyle="outline" onClick={() => setShowPreview((v) => !v)}>
                    Preview slurm command
                  </Button>
                </Box>
              )}
              {showPreview && (
                <Box sx={{ mt: 2 }}>
                  <CommandBox text={job?.push_command ?? DEFAULT_PUSH_COMMAND} />
                </Box>
              )}
              <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 1.5 }}>
                Runs{' '}
                <Box component="span" sx={{ fontFamily: 'monospace' }}>
                  {job?.push_command ?? DEFAULT_PUSH_COMMAND}
                </Box>{' '}
                — submits a SLURM job to upload files to S3.
              </Typography>
            </Box>
          )}

          {focus === 3 && (
            <Box sx={{ border: '1px solid', borderColor: 'divider', borderRadius: 2, p: 2 }}>
              <Typography variant="subtitle2" sx={{ fontWeight: 700, mb: 1 }}>
                {pushHeading(pushed)}
              </Typography>
              {pushed === 'active' && <LinearProgress sx={{ my: 1 }} />}
              {job?.push_slurm_job_id && (
                <Typography variant="caption" color="text.secondary">
                  SLURM job {job.push_slurm_job_id}
                </Typography>
              )}
              {pushed !== 'error' && (
                <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 1 }}>
                  Upload byte-progress isn&apos;t available yet.
                </Typography>
              )}
              {!readOnly && pushed === 'error' && (
                <Box sx={{ mt: 2 }}>
                  <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 1.5 }}>
                    Recovery restarts from preparation — the upload becomes available again once prep completes.
                  </Typography>
                  <Button sdsType="primary" sdsStyle="solid" disabled={submit.isPending} onClick={runSync}>
                    {submit.isPending ? 'Restarting…' : 'Restart preparation'}
                  </Button>
                </Box>
              )}
            </Box>
          )}

          {state === 'failed' && (
            <Alert severity="error">{errorMessage || 'Submission failed. You can try again.'}</Alert>
          )}
          {pushed === 'done' && <Alert severity="success">Submitted — uploaded to the data portal.</Alert>}
          {actionError && <Alert severity="error">{actionError}</Alert>}
        </Stack>

        {/* Right: live log + email */}
        <Stack spacing={2}>
          <LiveLog text={job?.log_excerpt} />
          <Tooltip title="Email notifications aren't wired up yet.">
            <FormControlLabel
              control={<Checkbox checked disabled />}
              label={
                <Box>
                  <Typography variant="body2">Email me when this finishes</Typography>
                  <Typography variant="caption" color="text.secondary">
                    You can close this tab - sync, validation and push keep running.
                  </Typography>
                </Box>
              }
            />
          </Tooltip>
        </Stack>
      </Box>

      {ssh && (
        <SSHSetupModal
          open
          cluster={ssh.cluster as 'czii' | 'bruno'}
          defaultUsername={ssh.username}
          onClose={() => setSsh(null)}
          onSuccess={() => {
            const { phase } = ssh;
            setSsh(null);
            if (phase === 'push') runPush();
            else runSync();
          }}
        />
      )}
    </Stack>
  );
}
