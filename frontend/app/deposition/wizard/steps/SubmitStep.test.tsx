import '@testing-library/jest-dom';
import { act, fireEvent, render, screen } from '@testing-library/react';

import { SubmitStep } from './SubmitStep';
import { isActiveJobState, useSubmitFlow } from '../../hooks/useSubmitFlow';
import { useDatasetLogs } from '../../hooks/useDatasetLogs';
import type { Dataset, DatasetJob, JobLogs } from '../../types';

jest.mock('../../hooks/useSubmitFlow', () => ({
  useSubmitFlow: jest.fn(),
  isActiveJobState: jest.fn(() => false),
}));
jest.mock('../../hooks/useDatasetLogs', () => ({ useDatasetLogs: jest.fn(() => ({ data: undefined })) }));
const mockFlow = useSubmitFlow as jest.Mock;
const mockLogs = useDatasetLogs as jest.Mock;
const mockActive = isActiveJobState as jest.Mock;

function setLogs(data: JobLogs | undefined) {
  mockLogs.mockReturnValue({ data });
}

function setup(job: DatasetJob | null, { readOnly = false } = {}) {
  const submit = { mutate: jest.fn(), reset: jest.fn(), isPending: false, isError: false, error: null };
  const push = { mutate: jest.fn(), reset: jest.fn(), isPending: false, isError: false, error: null };
  const dataset = { id: 1, title: 'DS', dataset_id: 2, status: 'draft', job } as Dataset;
  mockFlow.mockReturnValue({ dataset, submit, push });
  render(<SubmitStep dataset={dataset} readOnly={readOnly} reportSave={jest.fn()} />);
  return { submit, push };
}

beforeEach(() => {
  jest.clearAllMocks();
  mockLogs.mockReturnValue({ data: undefined });
  mockActive.mockReturnValue(false);
});

it('auto-starts sync on arrival with no manual start button', () => {
  const { submit } = setup(null);
  expect(submit.mutate).toHaveBeenCalled();
  expect(screen.queryByRole('button', { name: /submit for preparation/i })).toBeNull();
});

it('offers Submit deposition once prep is complete', () => {
  const { push } = setup({ id: 1, state: 'prep_completed' });
  fireEvent.click(screen.getByRole('button', { name: /submit deposition/i }));
  expect(push.mutate).toHaveBeenCalled();
});

it('shows a retry action and the error when sync failed', () => {
  setup({ id: 1, state: 'failed', error_message: 'sync blew up' });
  expect(screen.getByText('sync blew up')).toBeInTheDocument();
  expect(screen.getByRole('button', { name: /retry sync/i })).toBeInTheDocument();
});

it('shows success and no submit actions once pushed', () => {
  setup({ id: 1, state: 'completed', push_slurm_job_id: '99' });
  expect(screen.getByText(/uploaded to the data portal/i)).toBeInTheDocument();
  expect(screen.queryByRole('button', { name: /submit/i })).toBeNull();
});

it('hides submit actions and does not auto-start in read-only mode', () => {
  const { submit } = setup(null, { readOnly: true });
  expect(screen.queryByRole('button', { name: /submit/i })).toBeNull();
  expect(submit.mutate).not.toHaveBeenCalled();
});

it('shows which dataset is being submitted', () => {
  setup(null);
  expect(screen.getByText('DS (#2)')).toBeInTheDocument();
});

it('offers retry when the launch is rejected before a job exists', () => {
  const submit = {
    mutate: jest.fn(),
    reset: jest.fn(),
    isPending: false,
    isError: true,
    error: new Error('Missing dataset ids'),
  };
  const push = { mutate: jest.fn(), reset: jest.fn(), isPending: false, isError: false, error: null };
  const dataset = { id: 1, title: 'DS', dataset_id: 2, status: 'draft', job: null } as Dataset;
  mockFlow.mockReturnValue({ dataset, submit, push });
  render(<SubmitStep dataset={dataset} readOnly={false} reportSave={jest.fn()} />);
  expect(screen.getByText('Missing dataset ids')).toBeInTheDocument();
  expect(screen.getByRole('button', { name: /retry sync/i })).toBeInTheDocument();
});

it('renders live progress from the job payload', () => {
  setup({
    id: 1,
    state: 'prep_running',
    sync_progress: {
      done: 1883,
      total: 2215,
      eta: '0:05',
      items: [{ label: 'Symlink tiltseries', done: 582, total: 582 }],
    },
  });
  expect(screen.getByText(/1,883 \/ 2,215 objects/)).toBeInTheDocument();
  expect(screen.getByText('Symlink tiltseries')).toBeInTheDocument();
  expect(screen.getByText('582 / 582')).toBeInTheDocument();
});

it('shows a clean validation pass as success, not a warning', () => {
  setup({ id: 1, state: 'prep_completed', validation: { passed: true, warnings: [] } });
  expect(screen.getByText('Validation passed')).toBeInTheDocument();
  expect(screen.queryByText(/0 warnings/)).toBeNull();
});

it('blocks submit on a failing validation', () => {
  setup({
    id: 1,
    state: 'prep_completed',
    validation: { passed: false, warnings: [{ message: 'bad voxel spacing' }] },
  });
  expect(screen.getByText('Validation found blocking issues')).toBeInTheDocument();
  expect(screen.getByRole('button', { name: /submit deposition/i })).toBeDisabled();
});

it('recovers a failed push by restarting prep, not re-pushing', () => {
  const { submit, push } = setup({ id: 1, state: 'failed', push_slurm_job_id: '99', error_message: 'upload died' });
  const retry = screen.getByRole('button', { name: /restart preparation/i });
  expect(screen.queryByRole('button', { name: /retry upload/i })).toBeNull();
  fireEvent.click(retry);
  expect(submit.mutate).toHaveBeenCalled();
  expect(push.mutate).not.toHaveBeenCalled();
});

it('shows the live log tail from the logs endpoint', () => {
  setLogs({ logs: '[14:08] re-synced run002\n[14:12] skipping tomo_001.mrc', source: 'live' });
  setup({ id: 1, state: 'prep_running' });
  expect(screen.getByText('[14:08] re-synced run002')).toBeInTheDocument();
  expect(screen.getByText('[14:12] skipping tomo_001.mrc')).toBeInTheDocument();
});

it('promises a retry when an active job log is temporarily unavailable', () => {
  mockActive.mockReturnValue(true);
  setLogs({ logs: '', source: 'unavailable' });
  setup({ id: 1, state: 'prep_running' });
  expect(screen.getByText(/retrying/i)).toBeInTheDocument();
});

it('does not promise a retry once a finished job log is unavailable', () => {
  mockActive.mockReturnValue(false);
  setLogs({ logs: '', source: 'unavailable' });
  setup({ id: 1, state: 'failed' });
  expect(screen.queryByText(/retrying/i)).toBeNull();
  expect(screen.getByText(/couldn.t read the log/i)).toBeInTheDocument();
});

it('shows queued uploads without claiming they are uploading', () => {
  setup({ id: 1, state: 'push_submitted', push_slurm_job_id: '99' });
  expect(screen.getByText('Waiting in queue')).toBeInTheDocument();
  expect(screen.getByText('Upload job submitted. Detailed progress is unavailable.')).toBeInTheDocument();
});

it('distinguishes a running upload from unavailable detailed progress', () => {
  setup({ id: 1, state: 'push_running', push_slurm_job_id: '99' });
  expect(screen.getByText('Upload job in progress')).toBeInTheDocument();
  expect(screen.getByText('Upload job in progress. Detailed progress is unavailable.')).toBeInTheDocument();
});

it('updates sync elapsed time, freezes on completion and resets on restart', () => {
  jest.useFakeTimers();
  jest.setSystemTime(new Date('2026-10-14T12:02:00Z'));
  try {
    const job: DatasetJob = { id: 1, state: 'prep_running', started_at: '2026-10-14T12:00:00Z' };
    const dataset = { id: 1, title: 'DS', status: 'syncing', job } as Dataset;
    mockFlow.mockReturnValue({ dataset, submit: { isPending: false }, push: {} });
    const props = { dataset, readOnly: true, reportSave: jest.fn() };
    const view = render(<SubmitStep {...props} />);
    expect(screen.getByText(/Elapsed: 2m 0s/)).toBeInTheDocument();
    act(() => jest.advanceTimersByTime(2000));
    expect(screen.getByText(/Elapsed: 2m 2s/)).toBeInTheDocument();
    job.state = 'prep_completed';
    job.prep_completed_at = '2026-10-14T12:02:02Z';
    view.rerender(<SubmitStep {...props} />);
    act(() => jest.advanceTimersByTime(60000));
    expect(screen.getByText(/Completed in: 2m 2s/)).toBeInTheDocument();
    job.state = 'prep_running';
    job.started_at = new Date(Date.now()).toISOString();
    job.prep_completed_at = null;
    view.rerender(<SubmitStep {...props} />);
    act(() => jest.advanceTimersByTime(1000));
    expect(screen.getByText(/Elapsed: 0m 1s/)).toBeInTheDocument();
    view.unmount();
    expect(jest.getTimerCount()).toBe(0);
  } finally {
    jest.useRealTimers();
  }
});

it('keeps the saved sync duration while a later push is running', () => {
  setup({
    id: 1,
    state: 'push_running',
    push_slurm_job_id: '99',
    started_at: '2026-10-14T12:00:00Z',
    prep_completed_at: '2026-10-14T12:03:42Z',
  });
  expect(screen.getByText(/Completed in: 3m 42s/)).toBeInTheDocument();
});

it('shows the duration of a failed sync', () => {
  setup({ id: 1, state: 'failed', started_at: '2026-10-14T12:00:00Z', completed_at: '2026-10-14T12:00:42Z' });
  expect(screen.getByText(/Stopped after: 0m 42s/)).toBeInTheDocument();
});

it.each(['prep', 'push'])('shows one request error instead of the saved %s failure', (phase) => {
  const mutation = () => ({
    mutate: jest.fn(),
    reset: jest.fn(),
    isPending: false,
    isError: false,
    error: null as Error | null,
  });
  const submit = mutation();
  const push = mutation();
  const failed = phase === 'prep' ? submit : push;
  failed.isError = true;
  failed.error = new Error("Couldn't reach the cluster to submit. Please try again.");
  const dataset = {
    id: 1,
    title: 'DS',
    status: 'failed',
    job: {
      id: 1,
      state: 'failed',
      error_message: 'Failed to submit the job.',
      push_slurm_job_id: phase === 'push' ? '99' : null,
    },
  } as Dataset;
  mockFlow.mockReturnValue({ dataset, submit, push });
  render(<SubmitStep dataset={dataset} readOnly={false} reportSave={jest.fn()} />);
  expect(screen.getAllByRole('alert')).toHaveLength(1);
  expect(screen.getByRole('alert')).toHaveTextContent("Couldn't reach the cluster to submit. Please try again.");
  expect(screen.queryByText('Failed to submit the job.')).toBeNull();
});

it('shows one generic failure when no request or saved message is available', () => {
  setup({ id: 1, state: 'failed' });
  expect(screen.getAllByRole('alert')).toHaveLength(1);
  expect(screen.getByRole('alert')).toHaveTextContent('Submission failed. You can try again.');
});

it('lets users review each phase without launching another job', () => {
  mockLogs.mockImplementation((_id: number, { phase }: { phase: string }) => ({
    data: { logs: phase === 'prep' ? 'original prep output' : 'push output', source: 'live', phase },
  }));
  const { submit, push } = setup({ id: 1, state: 'failed', prep_slurm_job_id: '11', push_slurm_job_id: '99' });
  expect(screen.getByText('Upload log (tail)')).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: 'Sync on cluster' }));
  expect(screen.getByRole('button', { name: 'Sync on cluster' })).toHaveAttribute('aria-pressed', 'true');
  expect(screen.getByText('Sync log (tail)')).toBeInTheDocument();
  expect(screen.getByText('original prep output')).toBeInTheDocument();
  expect(screen.queryByText('push output')).toBeNull();
  fireEvent.click(screen.getByRole('button', { name: 'Pre-flight validation' }));
  expect(screen.getByText('Pre-flight validation is not available yet.')).toBeInTheDocument();
  expect(screen.queryByRole('button', { name: 'Submit deposition' })).toBeNull();
  expect(screen.queryByText('Sync log (tail)')).toBeNull();
  fireEvent.click(screen.getByRole('button', { name: 'Push to S3' }));
  expect(screen.getByText('push output')).toBeInTheDocument();
  expect(submit.mutate).not.toHaveBeenCalled();
  expect(push.mutate).not.toHaveBeenCalled();
});

it('does not offer an upload action when viewing validation before sync completes', () => {
  const { submit, push } = setup({ id: 1, state: 'prep_running' });
  fireEvent.click(screen.getByRole('button', { name: 'Pre-flight validation' }));
  expect(screen.queryByRole('button', { name: 'Submit deposition' })).toBeNull();
  expect(submit.mutate).not.toHaveBeenCalled();
  expect(push.mutate).not.toHaveBeenCalled();
});
