'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { Button, Icon } from '@czi-sds/components';
import { Alert, Box, ButtonBase, CircularProgress, LinearProgress, Stack, Typography } from '@mui/material';
import { ConfirmDialog } from '@app/common/components/Forms/ConfirmDialog';

import { formatBinaryBytes } from '@app/common/utils/format';

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

import { canUpload, isActiveJobPhase, submissionPhases, type PhaseStatus, type SubmitPhase } from '../../submitPhases';
import { groupSyncProgress } from '../../syncProgressGroups';
import { SubmissionLogPanel } from './SubmissionLogPanel';

const SYNC_TIMER_INTERVAL_MS = 1000;

const DETAIL_CARD_SX = {
  border: '1px solid',
  borderColor: 'divider',
  borderRadius: '8px',
  bgcolor: 'background.paper',
  p: { xs: '20px', lg: '28px' },
  minWidth: 0,
};

const PHASE_CARD_SX = {
  ...DETAIL_CARD_SX,
  height: 'var(--submission-panel-height)',
  overflow: 'auto',
  '&:focus-visible': { outline: '2px solid', outlineColor: 'primary.main', outlineOffset: -2 },
};

const DEFAULT_SYNC_COMMAND = 'cryoetportalprep sync ./dataprep_config.yaml';

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
  return total > 0 ? Math.min(100, Math.max(0, Math.round((done / total) * 100))) : 0;
}

function pluralWarnings(n: number): string {
  return `${n} warning${n === 1 ? '' : 's'}`;
}

function syncSub(status: PhaseStatus, progress?: SyncProgress | null, summary?: SyncSummary | null): string {
  if (status === 'active') {
    if (!progress) return 'In progress';
    if (progress.total <= 0) return 'In progress';
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
  return validation?.status === 'unavailable' ? 'Unavailable' : 'Not run';
}

function validationSeverity(validation: JobValidation): 'success' | 'warning' | 'error' | 'info' {
  if (validation.status === 'unavailable') return 'info';
  if (validation.status !== 'passed') return 'error';
  return validation.warnings.length ? 'warning' : 'success';
}

function validationTitle(validation: JobValidation): string {
  if (validation.status === 'unavailable') return 'Validation unavailable';
  if (validation.status !== 'passed') return 'Validation found blocking issues';
  return validation.warnings.length
    ? `Validation passed with ${pluralWarnings(validation.warnings.length)}`
    : 'Validation passed';
}

function validationBody(validation: JobValidation): string {
  if (validation.status === 'unavailable')
    return 'The validation result could not be obtained. Retry preparation and validation before uploading.';
  if (validation.status !== 'passed') return 'These issues must be resolved before the deposition can be pushed.';
  return validation.warnings.length ? 'You can submit - review the warnings below before you do.' : 'You can submit.';
}

const PUSH_SUB: Record<Exclude<PhaseStatus, 'warning'>, string> = {
  idle: 'Waiting on submit',
  active: 'Upload job in progress',
  done: 'Complete',
  error: 'Failed',
};

function pushHeading(status: PhaseStatus, state: JobState | undefined): string {
  if (status === 'idle') return 'Upload not started';
  if (state === 'push_submitted') return 'Waiting for upload to start';
  if (status === 'error') return 'Push failed';
  return 'Pushing to S3';
}

function uploadNote(state: JobState | undefined): string {
  if (state === 'push_submitted') return 'Upload job submitted.';
  if (state === 'push_running') return 'Waiting for upload progress.';
  return 'Files have been uploaded to S3.';
}

function summaryLine(s: SyncSummary): string {
  return [`${s.objects.toLocaleString()} objects`, s.size, s.duration].filter(Boolean).join(' · ');
}

function EmptyCircle({ color = 'text.disabled', size = 20 }: { color?: string; size?: number }) {
  return (
    <Box
      sx={{ width: size, height: size, flexShrink: 0, borderRadius: '50%', border: '2px solid', borderColor: color }}
    />
  );
}

function PhaseIcon({ status }: { status: PhaseStatus }) {
  if (status === 'active') return <CircularProgress size={18} />;
  if (status === 'done') return <Icon sdsIcon="CheckCircle" sdsSize="s" color="green" />;
  if (status === 'warning') return <Icon sdsIcon="ExclamationMarkCircle" sdsSize="s" color="yellow" />;
  if (status === 'error') return <Icon sdsIcon="ExclamationMarkCircle" sdsSize="s" color="red" />;
  return <EmptyCircle size={16} />;
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
      sx={{
        flex: 1,
        minWidth: 0,
        p: 2,
        // Divider only when tiles sit in a row; stacked (xs) it would be a stray right edge.
        borderRight: (theme) => ({
          xs: 'none',
          sm: n < 3 ? `1px solid ${theme.palette.divider}` : 'none',
        }),
        textAlign: 'left',
        '&.Mui-focusVisible': { outline: '2px solid', outlineColor: 'primary.main', outlineOffset: -2 },
        display: 'flex',
        gap: 1.5,
        alignItems: 'flex-start',
        borderBottom: '2px solid',
        borderBottomColor: active ? 'primary.main' : 'transparent',
      }}
    >
      <PhaseIcon status={status} />
      <Box>
        <Typography variant="body2" sx={{ fontWeight: 700 }}>
          {n} · {title}
        </Typography>
        <Typography
          variant="caption"
          color={
            {
              done: 'success.dark',
              warning: 'warning.dark',
              error: 'error.main',
              idle: 'text.secondary',
              active: 'primary.main',
            }[status]
          }
        >
          {sub}
        </Typography>
      </Box>
    </ButtonBase>
  );
}

function CommandBox({ text }: { text: string }) {
  return (
    <Box sx={{ bgcolor: 'grey.100', border: '1px solid', borderColor: 'divider', borderRadius: '6px', p: '12px 16px' }}>
      <Typography
        variant="body2"
        noWrap
        title={text}
        sx={{ fontFamily: 'monospace', display: 'block', lineHeight: 1.6 }}
      >
        {text}
      </Typography>
    </Box>
  );
}

function SyncChecklist({ items, selectedAnnotations }: { items: SyncChecklistItem[]; selectedAnnotations: number }) {
  const rows = groupSyncProgress(items)
    .filter((item) => item.label !== 'Deposit annotations')
    .map((item) => {
      const complete = item.total > 0 && item.done === item.total;
      return {
        label: item.label,
        count: `${item.done.toLocaleString()} / ${item.total.toLocaleString()}`,
        description: `${item.label}: ${item.done} of ${item.total}, ${complete ? 'complete' : 'incomplete'}`,
        complete,
      };
    });
  if (selectedAnnotations > 0) {
    const count = `${selectedAnnotations.toLocaleString()} annotation${selectedAnnotations === 1 ? '' : 's'} selected`;
    const otherIndex = rows.findIndex((row) => row.label === 'Other items');
    rows.splice(otherIndex === -1 ? rows.length : otherIndex, 0, {
      label: 'Deposit annotations',
      count,
      description: `Deposit annotations: ${count}`,
      complete: false,
    });
  }
  if (rows.length === 0) return null;
  return (
    <Stack
      role="list"
      aria-label="Sync progress by group"
      sx={{ mt: '20px', border: '1px solid', borderColor: 'divider', borderRadius: '6px', overflow: 'hidden' }}
    >
      {rows.map(({ label, count, description, complete }) => {
        return (
          <Box
            key={label}
            role="listitem"
            aria-label={description}
            sx={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              gap: '16px',
              p: '12px 16px',
              minHeight: 48,
              '& + &': { borderTop: '1px solid', borderColor: 'divider' },
            }}
          >
            <Box sx={{ display: 'flex', alignItems: 'center', gap: '12px', minWidth: 0 }}>
              {complete ? (
                <Icon sdsIcon="CheckCircle" sdsSize="s" color="green" />
              ) : (
                <EmptyCircle color="primary.main" size={16} />
              )}
              <Typography variant="body2">{label}</Typography>
            </Box>
            <Typography
              variant="body2"
              sx={{
                color: complete ? 'success.main' : 'primary.main',
                fontVariantNumeric: 'tabular-nums',
                whiteSpace: 'nowrap',
              }}
            >
              {count}
            </Typography>
          </Box>
        );
      })}
    </Stack>
  );
}

function WarningsList({ warnings, blocking }: { warnings: ValidationWarning[]; blocking?: boolean }) {
  return (
    <Box sx={{ border: '1px solid', borderColor: 'divider', borderRadius: '6px', mt: '20px' }}>
      {warnings.map((w, i) => (
        <Box
          key={`${w.message}-${i}`}
          sx={{ display: 'flex', gap: '12px', p: '16px', borderTop: i ? '1px solid' : 'none', borderColor: 'divider' }}
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

export function SubmitStep({ dataset, readOnly }: StepProps) {
  const { submit, push, cancel: cancelUpload } = useSubmitFlow(dataset.id, dataset.deposition);
  const [cancelJobId, setCancelJobId] = useState<string | null>(null);
  const [selection, setSelection] = useState<{ datasetId: number; phase: 1 | 2 | 3 } | null>(null);
  const started = useRef(false);

  const job = dataset.job;
  const state = job?.state;
  const { sync, pushed, validation, focus: defaultFocus } = submissionPhases(job);
  const focus = selection?.datasetId === dataset.id ? selection.phase : defaultFocus;
  const logPhase: SubmitPhase = focus === 3 ? 'push' : 'prep';
  const logActive = isActiveJobPhase(state, logPhase);
  const logs = useDatasetLogs(dataset.id, { state, phase: logPhase, enabled: !!job && dataset.is_owner !== false });

  const { mutate: prepare, reset: resetSubmit } = submit;
  const { reset: resetPush } = push;
  const runSync = useCallback(() => {
    setSelection(null);
    resetSubmit();
    resetPush();
    prepare();
  }, [prepare, resetSubmit, resetPush]);
  const runPush = () => {
    setSelection(null);
    push.reset();
    submit.reset();
    push.mutate();
  };

  // Intentional: entering Finalize, including after reset, starts prep once per mount.
  // The server's atomic claim prevents concurrent launches across tabs.
  useEffect(() => {
    if (!readOnly && sync === 'idle' && !submit.isPending && !started.current) {
      started.current = true;
      runSync();
    }
  }, [readOnly, sync, submit.isPending, runSync]);

  const selectedAnnotations = (dataset.sessions ?? []).reduce(
    (count, session) => count + (session.annotations ?? []).filter((annotation) => annotation.is_selected).length,
    0
  );
  const progress = job?.sync_progress ?? null;
  const uploadProgress = job?.push_progress ?? null;
  const uploadTotalEstimated = uploadProgress?.estimated ?? uploadProgress?.objects?.estimated ?? false;
  const summary = job?.sync_summary ?? null;
  const warnings = job?.validation?.warnings ?? [];
  const blockingIssues = job?.validation?.blocking_issues ?? [];
  const canPush = canUpload(job);
  const actionPending = submit.isPending || push.isPending || cancelUpload.isPending;
  const uploadActive = isActiveJobPhase(state, 'push');
  let uploadHeading = pushHeading(pushed, state);
  if (uploadActive && uploadProgress) uploadHeading = 'Uploading to S3';
  if (job?.error_message === 'Upload cancelled.') uploadHeading = 'Upload cancelled';
  const cancellationRequested = cancelUpload.isSuccess && cancelUpload.variables === job?.push_slurm_job_id;

  const actionError = (submit.error as Error | null)?.message || (push.error as Error | null)?.message;
  const errorMessage =
    actionError || (state === 'failed' ? job?.error_message || 'Submission failed. You can try again.' : null);

  const retryLabel = pushed === 'error' ? 'Restart preparation' : 'Retry sync';

  const sessionCount = dataset.session_count ?? dataset.sessions?.length ?? 0;
  const datasetLabel = dataset.dataset_id ? `${dataset.title} (#${dataset.dataset_id})` : dataset.title;

  return (
    <Stack spacing={{ xs: '16px', lg: '24px' }} useFlexGap sx={{ '@media (max-height: 800px)': { gap: '12px' } }}>
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
      <Box
        sx={{
          display: 'flex',
          flexDirection: { xs: 'column', sm: 'row' },
          border: '1px solid',
          borderColor: 'divider',
          borderRadius: 2,
          bgcolor: 'background.paper',
          overflow: 'hidden',
        }}
      >
        <PhaseTile
          n={1}
          title="Sync on cluster"
          status={sync}
          active={focus === 1}
          onSelect={() => setSelection({ datasetId: dataset.id, phase: 1 })}
          sub={
            <>
              {state === 'prep_submitted' ? 'Waiting in queue' : syncSub(sync, progress, summary)}
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

      <Box
        sx={{
          display: 'grid',
          gridTemplateColumns: { xs: 'minmax(0, 1fr)', md: 'minmax(0, 1.2fr) minmax(0, 1fr)' },
          gap: { xs: '16px', lg: '24px' },
          alignItems: 'start',
          '--submission-panel-height': 'clamp(280px, 40dvh, 480px)',
          '@media (max-height: 800px)': {
            gap: '16px',
            '--submission-panel-height': 'clamp(240px, 38dvh, 320px)',
          },
        }}
      >
        {/* Left: phase detail + actions */}
        <Stack spacing="16px" sx={{ minWidth: 0 }}>
          {focus === 1 && (
            <Box role="region" aria-label="Sync details" tabIndex={0} sx={{ ...PHASE_CARD_SX, p: '20px' }}>
              <Box sx={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap', gap: '8px', mb: '20px' }}>
                <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>
                  {sync === 'done' ? 'Local sync complete' : 'Local sync on cluster'}
                </Typography>
                {summary && sync === 'done' && (
                  <Typography variant="body2" color="text.secondary">
                    · {summaryLine(summary)}
                  </Typography>
                )}
              </Box>
              <CommandBox text={job?.sync_command ?? DEFAULT_SYNC_COMMAND} />
              {progress && progress.total > 0 ? (
                <>
                  <LinearProgress
                    aria-label="Sync progress"
                    variant="determinate"
                    value={toPct(progress.done, progress.total)}
                    sx={{ mt: '16px', height: 8, borderRadius: '6px' }}
                  />
                  <Box
                    sx={{ display: 'flex', justifyContent: 'space-between', flexWrap: 'wrap', gap: '8px', mt: '8px' }}
                  >
                    <Typography variant="body2" color="text.secondary">
                      {progress.done.toLocaleString()} / {progress.total.toLocaleString()} objects
                    </Typography>
                    <Typography variant="body2" sx={{ color: 'primary.main', fontWeight: 700 }}>
                      {toPct(progress.done, progress.total)}%
                      {progress.eta && sync === 'active' ? ` · ETA ${progress.eta}` : ''}
                    </Typography>
                  </Box>
                </>
              ) : (
                <>
                  {sync === 'active' && (
                    <LinearProgress aria-label="Sync progress" sx={{ mt: '16px', height: 8, borderRadius: '6px' }} />
                  )}
                  <Typography variant="body2" color="text.secondary" sx={{ display: 'block', mt: '16px' }}>
                    {sync === 'active' || sync === 'idle'
                      ? 'Waiting for preparation progress.'
                      : 'Detailed progress is unavailable for this preparation.'}
                  </Typography>
                </>
              )}
              <SyncChecklist items={progress?.items ?? []} selectedAnnotations={selectedAnnotations} />
            </Box>
          )}

          {focus === 2 && (
            <Box role="region" aria-label="Validation details" tabIndex={0} sx={PHASE_CARD_SX}>
              {sync === 'done' && (
                <Box sx={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap', gap: 1 }}>
                  <Icon sdsIcon="CheckCircle" sdsSize="s" color="green" />
                  <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>
                    Local sync complete
                  </Typography>
                  {summary && (
                    <Typography variant="caption" color="text.secondary">
                      · {summaryLine(summary)}
                    </Typography>
                  )}
                </Box>
              )}

              <Typography variant="h6" sx={{ fontWeight: 700, mt: '24px', mb: '20px' }}>
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
                  {warnings.length > 0 && <WarningsList warnings={warnings} />}
                  {blockingIssues.length > 0 && <WarningsList warnings={blockingIssues} blocking />}
                </>
              ) : (
                <Alert severity="info">Pre-flight validation has not run. Upload requires a passed check.</Alert>
              )}
            </Box>
          )}

          {focus === 3 && (
            <Box
              role="region"
              aria-label="Upload details"
              tabIndex={0}
              sx={{ ...PHASE_CARD_SX, ...(pushed === 'done' ? { height: 'auto' } : {}) }}
            >
              <Box
                sx={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'flex-start',
                  flexWrap: 'wrap',
                  gap: '16px',
                  mb: '20px',
                }}
              >
                <Box sx={{ minWidth: 0 }}>
                  {pushed === 'done' ? (
                    <Alert severity="success" icon={<Icon sdsIcon="CheckCircle" sdsSize="s" color="green" />}>
                      <Typography variant="body2" sx={{ fontWeight: 700 }}>
                        Upload complete
                      </Typography>
                      <Typography variant="body2">{uploadNote(state)}</Typography>
                    </Alert>
                  ) : (
                    <Typography variant="h6" color="text.secondary">
                      {uploadHeading}
                    </Typography>
                  )}
                  {uploadProgress?.objects && (
                    <Typography variant="h4" sx={{ fontVariantNumeric: 'tabular-nums', mt: '4px' }}>
                      <Box component="span" sx={{ fontWeight: 700 }}>
                        {uploadProgress.objects.done.toLocaleString()}
                      </Box>
                      <Box component="span" sx={{ color: 'text.secondary' }}>
                        {uploadProgress.objects.total !== null &&
                          ` / ${uploadProgress.objects.estimated ? '~' : ''}${uploadProgress.objects.total.toLocaleString()}`}
                        {' objects uploaded'}
                      </Box>
                    </Typography>
                  )}
                </Box>
                {!readOnly && uploadActive && job?.push_slurm_job_id && (
                  <Box sx={{ '& button': { whiteSpace: 'nowrap' } }}>
                    <Button
                      sdsType="secondary"
                      sdsStyle="outline"
                      disabled={actionPending || cancellationRequested}
                      onClick={() => {
                        cancelUpload.reset();
                        setCancelJobId(job.push_slurm_job_id ?? null);
                      }}
                    >
                      {cancellationRequested ? 'Cancellation requested' : 'Cancel upload'}
                    </Button>
                    {cancellationRequested && (
                      <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                        Waiting for the cluster to confirm cancellation.
                      </Typography>
                    )}
                  </Box>
                )}
              </Box>
              {pushed === 'active' && (
                <LinearProgress
                  aria-label="Upload progress"
                  variant={
                    uploadProgress && uploadProgress.total > 0 && !uploadTotalEstimated
                      ? 'determinate'
                      : 'indeterminate'
                  }
                  value={uploadProgress ? toPct(uploadProgress.done, uploadProgress.total) : undefined}
                  sx={{ height: 8, borderRadius: '6px', mb: '20px' }}
                />
              )}
              <Box
                sx={{ display: 'flex', flexWrap: 'wrap', columnGap: '24px', rowGap: '8px', color: 'text.secondary' }}
              >
                {uploadProgress && uploadProgress.total > 0 && (
                  <Typography variant="body2">
                    Size{' '}
                    <Box component="span" sx={{ color: 'text.primary' }}>
                      {formatBinaryBytes(uploadProgress.done)} / {uploadTotalEstimated ? '~' : ''}
                      {formatBinaryBytes(uploadProgress.total)}
                    </Box>
                    {!uploadTotalEstimated && ` · ${toPct(uploadProgress.done, uploadProgress.total)}%`}
                    {uploadProgress.eta && pushed === 'active' && !uploadTotalEstimated
                      ? ` · ETA ${uploadProgress.eta}`
                      : ''}
                  </Typography>
                )}
                {uploadProgress?.elapsed && <Typography variant="body2">Elapsed: {uploadProgress.elapsed}</Typography>}
                {job?.push_slurm_job_id && <Typography variant="body2">SLURM job {job.push_slurm_job_id}</Typography>}
              </Box>
              {uploadTotalEstimated && pushed === 'active' && (
                <Typography variant="body2" color="text.secondary" sx={{ mt: '16px' }}>
                  Calculating total…
                </Typography>
              )}
              {pushed === 'active' && !uploadProgress && (
                <Typography variant="body2" color="text.secondary" sx={{ mt: '16px' }}>
                  {uploadNote(state)}
                </Typography>
              )}
            </Box>
          )}

          {!readOnly && state === 'prep_completed' && (
            <Box sx={DETAIL_CARD_SX}>
              {!canPush && (
                <Alert severity="warning" sx={{ mb: '16px' }}>
                  Validation must pass before upload. Prepare again, or edit metadata to fix the issues.
                </Alert>
              )}
              <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: '12px' }}>
                <Button sdsType="primary" sdsStyle="solid" disabled={actionPending || !canPush} onClick={runPush}>
                  {push.isPending ? 'Starting upload…' : 'Upload to S3'}
                </Button>
                <Button sdsType="secondary" sdsStyle="solid" disabled={actionPending} onClick={runSync}>
                  Prepare again
                </Button>
              </Box>
            </Box>
          )}
          {!readOnly && (sync === 'error' || pushed === 'error' || (submit.isError && !isActiveJobPhase(state))) && (
            <Box>
              {pushed === 'error' && (
                <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 1.5 }}>
                  Restart preparation and validation before uploading again.
                </Typography>
              )}
              <Button sdsType="primary" sdsStyle="solid" disabled={actionPending} onClick={runSync}>
                {submit.isPending ? 'Retrying…' : retryLabel}
              </Button>
            </Box>
          )}

          {errorMessage && (
            <Alert severity="error" sx={{ whiteSpace: 'pre-line' }}>
              {errorMessage}
            </Alert>
          )}
        </Stack>

        {/* Right: live log */}
        <Stack spacing="16px" sx={{ minWidth: 0 }}>
          <SubmissionLogPanel
            data={logs.data}
            active={logActive}
            phase={logPhase}
            restricted={dataset.is_owner === false}
          />
          {isActiveJobPhase(state) && (
            <Alert
              severity="info"
              sx={{ p: '16px 20px', border: '1px solid', borderColor: 'divider', borderRadius: '8px' }}
            >
              You can close this tab. The running cluster job will continue; return to My Submissions to check its
              status.
            </Alert>
          )}
        </Stack>
      </Box>
      <ConfirmDialog
        open={!readOnly && uploadActive && cancelJobId !== null && cancelJobId === job?.push_slurm_job_id}
        onClose={() => {
          if (!cancelUpload.isPending) setCancelJobId(null);
        }}
        onConfirm={() => {
          if (cancelJobId) cancelUpload.mutate(cancelJobId, { onSuccess: () => setCancelJobId(null) });
        }}
        title="Cancel upload?"
        heading="Stop this upload"
        body="The cluster upload job will be cancelled. Files already uploaded to S3 will remain."
        confirmText="Cancel upload"
        submittingText="Cancelling…"
        cancelText="Keep uploading"
        isSubmitting={cancelUpload.isPending}
        error={cancelUpload.error?.message}
      />
    </Stack>
  );
}
