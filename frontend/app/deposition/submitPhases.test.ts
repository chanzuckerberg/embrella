import { canUpload } from './submitPhases';
import type { DatasetJob } from './types';

const job: DatasetJob = {
  id: 1,
  state: 'prep_completed',
  prep_slurm_job_id: '42',
  validation: { status: 'passed', attempt: '42', warnings: [], blocking_issues: [] },
};

it('permits only a current pass with no blocking issues', () => {
  expect(canUpload(job)).toBe(true);
  expect(canUpload({ ...job, validation: { ...job.validation!, warnings: [{ message: 'review this' }] } })).toBe(true);
  expect(canUpload(null)).toBe(false);
  expect(canUpload({ ...job, validation: null })).toBe(false);
  expect(canUpload({ ...job, state: 'push_running' })).toBe(false);
  expect(canUpload({ ...job, prep_slurm_job_id: '' })).toBe(false);
  expect(canUpload({ ...job, validation: { ...job.validation!, attempt: 'old' } })).toBe(false);
  expect(canUpload({ ...job, validation: { ...job.validation!, blocking_issues: [{ message: 'bad' }] } })).toBe(false);
});

it.each(['failed', 'unavailable'] as const)('rejects %s', (status) => {
  expect(canUpload({ ...job, validation: { ...job.validation!, status } })).toBe(false);
});
