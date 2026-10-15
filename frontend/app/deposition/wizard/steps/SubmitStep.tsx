'use client';

import { useEffect, useRef, useState } from 'react';
import { Button, Icon } from '@czi-sds/components';
import { Alert, Box, ButtonBase, CircularProgress, LinearProgress, Stack, Typography } from '@mui/material';

import type {
  DatasetJob,
  JobState,
  JobValidation,
  SyncChecklistItem,
  SyncProgress,
  SyncSummary,
  ValidationWarning,
} from '../../types';
import type { StepProps } from '../wizardTypes';
import { useSubmitFlow } from '../../hooks/useSubmitFlow';
import { useDatasetLogs } from '../../hooks/useDatasetLogs';

import { isActiveJobPhase, submissionPhases, type PhaseStatus, type SubmitPhase } from '../../submitPhases';
import { SubmissionLogPanel } from './SubmissionLogPanel';

const SYNC_TIMER_INTERVAL_MS = 1000;

const DEFAULT_SYNC_COMMAND = 'cryoetportalprep sync ./dataprep_config.yaml';
const DEFAULT_PUSH_COMMAND = 'aws s3 sync <staged dir> <s3 bucket> --follow-symlinks';

function SyncTiming({ job }: { job: DatasetJob | null | undefined }) {
  const [now, setNow] = useState(() => Date.now());
  const active = isActiveJobPhase(job?.state, 'prep');
  const start = job?.started_at ? Date.parse(job.started_at) : NaN;
  const end = job?.prep_completed_at ?? (job?.state === 'failed' && !job.push_slurm_job_id ? job.completed_at : null);

  useEffect(() => {
    if (!active || !Number.isFinite(start)) return;
    const timer = setInterval(() => setNow(Date.now()), SYNC_TIMER_INTERVAL_MS);
    return () => clearInterval(timer);
  }, [active, start]);

  let finish = NaN;
  if (end) finish = Date.parse(end);
  else if (active) finish = now;
  if (!Number.isFinite(start) || !Number.isFinite(finish)) return null;
  const seconds = Math.max(0, Math.floor((finish - start) / 1000));
  const minutes = Math.floor(seconds / 60);
  let label = 'Stopped after';
  if (active) label = 'Elapsed';
  else if (job?.prep_completed_at) label = 'Completed in';
  return (
    <span title="Includes time waiting in the cluster queue">
      {' '}
      · {label}: {minutes}m {seconds % 60}s
    </span>
  );
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
  return validation.warnings.length ? 'You can submit - review the warnings below before you do.' : 'You can submit.';
}

const PUSH_SUB: Record<PhaseStatus, string> = {
  idle: 'Waiting on submit',
  active: 'Upload job in progress',
  done: 'Complete',
  warning: 'Upload job in progress',
  error: 'Failed',
};

function pushHeading(status: PhaseStatus, state: JobState | undefined): string {
  if (status === 'idle') return 'Upload not started';
  if (state === 'push_submitted') return 'Waiting for upload to start';
  if (status === 'done') return 'Pushed to the data portal';
  if (status === 'error') return 'Push failed';
  return 'Pushing to S3';
}

function uploadNote(state: JobState | undefined): string {
  if (state === 'push_submitted') return 'Upload job submitted. Detailed progress is unavailable.';
  if (state === 'push_running') return 'Upload job in progress. Detailed progress is unavailable.';
  return 'Upload complete.';
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
  onSelect,
}: {
  n: number;
  title: string;
  sub: React.ReactNode;
  status: PhaseStatus;
  active: boolean;
  onSelect: () => void;
}) {
  return (
    <ButtonBase
      onClick={onSelect}
      aria-pressed={active}
      aria-label={title}
      sx={{
        flex: 1,
        p: 2,
        textAlign: 'left',
        '&.Mui-focusVisible': { outline: '2px solid', outlineColor: 'primary.main', outlineOffset: -2 },
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
    </ButtonBase>
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

export function SubmitStep({ dataset: initial, readOnly }: StepProps) {
  const { dataset, submit, push } = useSubmitFlow(initial);
  const [selection, setSelection] = useState<{ datasetId: number; phase: 1 | 2 | 3 } | null>(null);
  const [showPreview, setShowPreview] = useState(false);
  const started = useRef(false);

  const job = dataset.job;
  const state = job?.state;
  const { sync, pushed, validation, focus: defaultFocus } = submissionPhases(job);
  const focus = selection?.datasetId === dataset.id ? selection.phase : defaultFocus;
  const logPhase: SubmitPhase = focus === 3 ? 'push' : 'prep';
  const logActive = isActiveJobPhase(state, logPhase);
  // focus === 2 is pre-flight validation; its log panel isn't rendered, so don't fetch (SSH read).
  const logs = useDatasetLogs(dataset.id, { state, phase: logPhase, enabled: !!job && focus !== 2 });

  const runSync = () => {
    setSelection(null);
    submit.reset();
    push.reset();
    submit.mutate();
  };
  const runPush = () => {
    setSelection(null);
    push.reset();
    submit.reset();
    push.mutate();
  };

  // Landing on this step kicks off the sync - no manual start button (matches the mock).
  useEffect(() => {
    if (!readOnly && sync === 'idle' && !submit.isPending && !started.current) {
      started.current = true;
      runSync();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- fire once on first idle render
  }, [readOnly, sync]);

  const progress = job?.sync_progress ?? null;
  const summary = job?.sync_summary ?? null;
  const warnings = job?.validation?.warnings ?? [];
  const canPush = !job?.validation || job.validation.passed;

  const actionError = (submit.error as Error | null)?.message || (push.error as Error | null)?.message;
  const errorMessage =
    actionError || (state === 'failed' ? job?.error_message || 'Submission failed. You can try again.' : null);

  const retryLabel = pushed === 'error' ? 'Restart preparation' : 'Retry sync';

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
          onSelect={() => setSelection({ datasetId: dataset.id, phase: 1 })}
          sub={
            <>
              {syncSub(sync, progress, summary)}
              <SyncTiming job={job} />
            </>
          }
        />
        <PhaseTile
          n={2}
          title="Pre-flight validation"
          status={validation}
          active={focus === 2}
          onSelect={() => setSelection({ datasetId: dataset.id, phase: 2 })}
          sub={validationSub(validation, job?.validation)}
        />
        <PhaseTile
          n={3}
          title="Push to S3"
          status={pushed}
          active={focus === 3}
          onSelect={() => setSelection({ datasetId: dataset.id, phase: 3 })}
          sub={state === 'push_submitted' ? 'Waiting in queue' : PUSH_SUB[pushed]}
        />
      </Box>

      {!readOnly && state === 'prep_completed' && (
        <Box>
          <Button sdsType="primary" sdsStyle="solid" disabled={push.isPending || !canPush} onClick={runPush}>
            {push.isPending ? 'Submitting…' : 'Submit deposition'}
          </Button>
        </Box>
      )}
      {!readOnly && (sync === 'error' || pushed === 'error' || submit.isError) && (
        <Box>
          {pushed === 'error' && (
            <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 1.5 }}>
              Recovery restarts from preparation - the upload becomes available again once prep completes.
            </Typography>
          )}
          <Button sdsType="primary" sdsStyle="solid" disabled={submit.isPending} onClick={runSync}>
            {submit.isPending ? 'Retrying…' : retryLabel}
          </Button>
        </Box>
      )}

      <Box
        sx={{
          display: 'grid',
          gridTemplateColumns: { xs: 'minmax(0, 1fr)', md: 'minmax(0, 1fr) minmax(0, 1fr)' },
          gap: 3,
        }}
      >
        {/* Left: phase detail + actions */}
        <Stack spacing={2}>
          {focus === 1 && (
            <Box sx={{ border: '1px solid', borderColor: 'divider', borderRadius: 2, p: 2 }}>
              <Typography variant="subtitle2" sx={{ fontWeight: 700, mb: 1.5 }}>
                {sync === 'done' ? 'Local sync complete' : 'Local sync on cluster'}
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
            </Box>
          )}

          {focus === 2 && (
            <Box sx={{ border: '1px solid', borderColor: 'divider', borderRadius: 2, p: 2 }}>
              {sync === 'done' && (
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
              )}

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
                <Alert severity="info">Pre-flight validation is not available yet.</Alert>
              )}

              {!readOnly && state === 'prep_completed' && (
                <Box sx={{ display: 'flex', gap: 2, mt: 2.5 }}>
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
                - submits a SLURM job to upload files to S3.
              </Typography>
            </Box>
          )}

          {focus === 3 && (
            <Box sx={{ border: '1px solid', borderColor: 'divider', borderRadius: 2, p: 2 }}>
              <Typography variant="subtitle2" sx={{ fontWeight: 700, mb: 1 }}>
                {pushHeading(pushed, state)}
              </Typography>
              {pushed === 'active' && <LinearProgress sx={{ my: 1 }} />}
              {job?.push_slurm_job_id && (
                <Typography variant="caption" color="text.secondary">
                  SLURM job {job.push_slurm_job_id}
                </Typography>
              )}
              {(pushed === 'active' || pushed === 'done') && (
                <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 1 }}>
                  {uploadNote(state)}
                </Typography>
              )}
            </Box>
          )}

          {errorMessage && <Alert severity="error">{errorMessage}</Alert>}
          {pushed === 'done' && <Alert severity="success">Submitted - uploaded to the data portal.</Alert>}
        </Stack>

        {/* Right: live log */}
        {focus !== 2 && (
          <Stack spacing={2}>
            <SubmissionLogPanel data={logs.data} active={logActive} phase={logPhase} />
          </Stack>
        )}
      </Box>
    </Stack>
  );
}
