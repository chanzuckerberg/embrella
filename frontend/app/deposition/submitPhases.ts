import type { DatasetJob, JobState, JobValidation } from './types';

export type SubmitPhase = 'prep' | 'push';
export type PhaseStatus = 'idle' | 'active' | 'done' | 'warning' | 'error';

export function isActiveJobPhase(state?: JobState | null, phase?: SubmitPhase): boolean {
  const prep = state === 'prep_submitted' || state === 'prep_running';
  const push = state === 'push_submitted' || state === 'push_running';
  if (phase === 'prep') return prep;
  if (phase === 'push') return push;
  return prep || push;
}

function syncStatus(state: JobState | undefined, hasPushId: boolean): PhaseStatus {
  if (!state || state === 'pending') return 'idle';
  if (isActiveJobPhase(state, 'prep')) return 'active';
  if (state === 'failed' && !hasPushId) return 'error';
  return 'done';
}

function validationStatus(validation: JobValidation | null | undefined): PhaseStatus {
  if (!validation) return 'idle';
  if (validation.status === 'unavailable') return 'idle';
  if (validation.status !== 'passed') return 'error';
  return validation.warnings.length ? 'warning' : 'done';
}

function pushStatus(state: JobState | undefined, hasPushId: boolean): Exclude<PhaseStatus, 'warning'> {
  if (isActiveJobPhase(state, 'push')) return 'active';
  if (state === 'completed') return 'done';
  if (state === 'failed' && hasPushId) return 'error';
  return 'idle';
}

function focusPhase(sync: PhaseStatus, push: PhaseStatus): 1 | 2 | 3 {
  if (push !== 'idle') return 3;
  if (sync === 'done') return 2;
  return 1;
}

export function submissionPhases(job: DatasetJob | null | undefined) {
  const state = job?.state;
  const hasPushId = !!job?.push_slurm_job_id;
  const sync = job?.sync_progress?.completed_at ? 'done' : syncStatus(state, hasPushId);
  const pushed = pushStatus(state, hasPushId);
  const validation =
    sync === 'done' && isActiveJobPhase(state, 'prep') && !job?.validation
      ? 'active'
      : validationStatus(job?.validation);
  return { sync, pushed, validation, focus: focusPhase(sync, pushed) };
}

export function canUpload(job: DatasetJob | null | undefined): boolean {
  return (
    job?.state === 'prep_completed' &&
    !!job.prep_slurm_job_id &&
    job.validation?.status === 'passed' &&
    job.validation.attempt === job.prep_slurm_job_id &&
    job.validation.blocking_issues.length === 0
  );
}
