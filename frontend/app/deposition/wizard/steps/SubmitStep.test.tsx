import '@testing-library/jest-dom';
import { act, fireEvent, render, screen } from '@testing-library/react';

import { SubmitStep } from './SubmitStep';
import { useSubmitFlow } from '../../hooks/useSubmitFlow';
import { useDatasetLogs } from '../../hooks/useDatasetLogs';
import type { Dataset, DatasetJob, JobLogs } from '../../types';

jest.mock('../../hooks/useSubmitFlow', () => ({
  useSubmitFlow: jest.fn(),
}));
jest.mock('../../hooks/useDatasetLogs', () => ({ useDatasetLogs: jest.fn(() => ({ data: undefined })) }));
const mockFlow = useSubmitFlow as jest.Mock;
const mockLogs = useDatasetLogs as jest.Mock;

function setLogs(data: JobLogs | undefined) {
  mockLogs.mockReturnValue({ data });
}

const passed = { status: 'passed' as const, attempt: 'prep-1', warnings: [], blocking_issues: [] };
const prepared: DatasetJob = { id: 1, state: 'prep_completed', prep_slurm_job_id: 'prep-1', validation: passed };

function setup(job: DatasetJob | null, { readOnly = false } = {}) {
  const submit = { mutate: jest.fn(), reset: jest.fn(), isPending: false, isError: false, error: null };
  const push = { mutate: jest.fn(), reset: jest.fn(), isPending: false, isError: false, error: null };
  const dataset = { id: 1, title: 'DS', dataset_id: 2, status: 'draft', job } as Dataset;
  mockFlow.mockReturnValue({ submit, push });
  const view = render(<SubmitStep dataset={dataset} readOnly={readOnly} reportSave={jest.fn()} />);
  return { submit, push, dataset, view };
}

beforeEach(() => {
  jest.clearAllMocks();
  mockLogs.mockReturnValue({ data: undefined });
});

it('auto-starts preparation once on arrival', () => {
  const { submit } = setup(null);
  expect(submit.mutate).toHaveBeenCalledTimes(1);
});

it('keeps a rejected pending attempt from retrying on rerenders, but allows manual retry and re-entry', () => {
  const { submit, push, dataset, view } = setup({ id: 1, state: 'pending' });
  expect(submit.mutate).toHaveBeenCalledTimes(1);
  mockFlow.mockReturnValue({
    submit: {
      ...submit,
      isError: true,
      error: new Error('Complete the metadata before preparation:\nDataset title is required.'),
    },
    push,
  });
  view.rerender(<SubmitStep dataset={dataset} readOnly={false} reportSave={jest.fn()} />);
  expect(screen.getByRole('alert')).toHaveTextContent('Dataset title is required.');
  expect(screen.getByRole('alert')).toHaveStyle({ whiteSpace: 'pre-line' });
  expect(submit.mutate).toHaveBeenCalledTimes(1);
  fireEvent.click(screen.getByRole('button', { name: 'Retry sync' }));
  expect(submit.mutate).toHaveBeenCalledTimes(2);
  view.unmount();

  const reentered = setup({ id: 1, state: 'pending' });
  expect(reentered.submit.mutate).toHaveBeenCalledTimes(1);
});

it('offers Upload to S3 once prep is complete', () => {
  const { push } = setup(prepared);
  fireEvent.click(screen.getByRole('button', { name: /upload to s3/i }));
  expect(push.mutate).toHaveBeenCalled();
});

it('shows a retry action and the error when sync failed', () => {
  setup({ id: 1, state: 'failed', error_message: 'sync blew up' });
  expect(screen.getByText('sync blew up')).toBeInTheDocument();
  expect(screen.getByRole('button', { name: /retry sync/i })).toBeInTheDocument();
});

it('shows success and no submit actions once pushed', () => {
  setup({ id: 1, state: 'completed', push_slurm_job_id: '99' });
  expect(screen.getByText(/Files have been uploaded to S3/i)).toBeInTheDocument();
  expect(screen.queryByRole('button', { name: /submit/i })).toBeNull();
});

it('hides submit actions and does not auto-start in read-only mode', () => {
  const { submit } = setup(null, { readOnly: true });
  expect(screen.queryByRole('button', { name: /upload to s3/i })).toBeNull();
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
  mockFlow.mockReturnValue({ submit, push });
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
      items: [{ label: 'Tilt series', done: 582, total: 582 }],
    },
  });
  expect(screen.getByText(/1,883 \/ 2,215 objects/)).toBeInTheDocument();
  expect(screen.getByRole('button', { name: /Sync on cluster/ })).toHaveTextContent('85% · ETA 0:05');
  expect(screen.getByText('Symlink tiltseries')).toBeInTheDocument();
  expect(screen.getByText('582 / 582')).toBeInTheDocument();
});

it('shows a clean validation pass as success, not a warning', () => {
  setup({ id: 1, state: 'prep_completed', prep_slurm_job_id: 'prep-1', validation: passed });
  expect(screen.getByText('Validation passed')).toBeInTheDocument();
  expect(screen.queryByText(/0 warnings/)).toBeNull();
});

it('blocks submit on a failing validation', () => {
  setup({
    id: 1,
    state: 'prep_completed',
    validation: { ...passed, status: 'failed', blocking_issues: [{ message: 'bad voxel spacing' }] },
  });
  expect(screen.getByText('Validation found blocking issues')).toBeInTheDocument();
  expect(screen.getByRole('button', { name: /upload to s3/i })).toBeDisabled();
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
  setLogs({ logs: '', source: 'unavailable' });
  setup({ id: 1, state: 'prep_running' });
  expect(screen.getByText(/retrying/i)).toBeInTheDocument();
});

it('does not promise a retry once a finished job log is unavailable', () => {
  setLogs({ logs: '', source: 'unavailable' });
  setup({ id: 1, state: 'failed' });
  expect(screen.queryByText(/retrying/i)).toBeNull();
  expect(screen.getByText(/couldn.t read the log/i)).toBeInTheDocument();
});

it('shows queued uploads without claiming they are uploading', () => {
  setup({ id: 1, state: 'push_submitted', push_slurm_job_id: '99' });
  expect(screen.getByText('Waiting in queue')).toBeInTheDocument();
  expect(screen.getByText('Upload job submitted.')).toBeInTheDocument();
});

it('distinguishes a running upload from unavailable detailed progress', () => {
  setup({ id: 1, state: 'push_running', push_slurm_job_id: '99' });
  expect(screen.getByText('Upload job in progress')).toBeInTheDocument();
  expect(screen.getByText('Waiting for upload progress.')).toBeInTheDocument();
});

it('updates sync elapsed time, freezes on completion and resets on restart', () => {
  jest.useFakeTimers();
  jest.setSystemTime(new Date('2026-10-14T12:02:00Z'));
  try {
    const job: DatasetJob = { id: 1, state: 'prep_running', started_at: '2026-10-14T12:00:00Z' };
    const dataset = { id: 1, title: 'DS', status: 'syncing', job } as Dataset;
    mockFlow.mockReturnValue({
      submit: { isPending: false },
      push: {},
    });
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
  mockFlow.mockReturnValue({ submit, push });
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
  fireEvent.click(screen.getByRole('button', { name: /Sync on cluster/ }));
  expect(screen.getByRole('button', { name: /Sync on cluster/ })).toHaveAttribute('aria-pressed', 'true');
  expect(screen.getByText('Sync log (tail)')).toBeInTheDocument();
  expect(screen.getByText('original prep output')).toBeInTheDocument();
  expect(screen.queryByText('push output')).toBeNull();
  fireEvent.click(screen.getByRole('button', { name: /Pre-flight validation/ }));
  expect(screen.getByText('Pre-flight validation has not run. Upload requires a passed check.')).toBeInTheDocument();
  expect(screen.queryByRole('button', { name: 'Upload to S3' })).toBeNull();
  expect(screen.getByText('Sync log (tail)')).toBeInTheDocument();
  expect(screen.getByText('original prep output')).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: /Push to S3/ }));
  expect(screen.getByText('push output')).toBeInTheDocument();
  expect(submit.mutate).not.toHaveBeenCalled();
  expect(push.mutate).not.toHaveBeenCalled();
});

it('does not offer an upload action when viewing validation before sync completes', () => {
  const { submit, push } = setup({ id: 1, state: 'prep_running' });
  fireEvent.click(screen.getByRole('button', { name: /Pre-flight validation/ }));
  expect(screen.queryByRole('button', { name: 'Upload to S3' })).toBeNull();
  expect(submit.mutate).not.toHaveBeenCalled();
  expect(push.mutate).not.toHaveBeenCalled();
});

it('keeps a manually selected sync log open when prep completes', () => {
  const job: DatasetJob = { id: 1, state: 'prep_running' };
  const dataset = { id: 1, title: 'DS', status: 'syncing', job } as Dataset;
  mockFlow.mockReturnValue({
    submit: { isPending: false },
    push: {},
  });
  const props = { dataset, readOnly: false, reportSave: jest.fn() };
  const view = render(<SubmitStep {...props} />);
  fireEvent.click(screen.getByRole('button', { name: /Sync on cluster/ }));
  job.state = 'prep_completed';
  view.rerender(<SubmitStep {...props} />);
  expect(screen.getByRole('button', { name: /Sync on cluster/ })).toHaveAttribute('aria-pressed', 'true');
  expect(screen.getByText('Sync log (tail)')).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: /Pre-flight validation/ }));
  expect(screen.getByRole('button', { name: 'Upload to S3' })).toBeInTheDocument();
});

it.each(['Sync on cluster', 'Pre-flight validation', 'Push to S3'])(
  'keeps submit accessible while viewing %s',
  (tile) => {
    const { push } = setup(prepared);
    fireEvent.click(screen.getByRole('button', { name: new RegExp(tile) }));
    fireEvent.click(screen.getByRole('button', { name: 'Upload to S3' }));
    expect(push.mutate).toHaveBeenCalledTimes(1);
  }
);

it.each(['Sync on cluster', 'Pre-flight validation', 'Push to S3'])(
  'keeps retry accessible while viewing %s',
  (tile) => {
    const { submit } = setup({ id: 1, state: 'failed' });
    fireEvent.click(screen.getByRole('button', { name: new RegExp(tile) }));
    fireEvent.click(screen.getByRole('button', { name: 'Retry sync' }));
    expect(submit.mutate).toHaveBeenCalledTimes(1);
  }
);

it('labels the saved excerpt when the live log is unavailable', () => {
  setLogs({ logs: 'saved failure output', source: 'unavailable' });
  setup({ id: 1, state: 'failed' });
  expect(screen.getByText('saved failure output')).toBeInTheDocument();
  expect(screen.getByText('Showing the saved output; the live log is unavailable.')).toBeInTheDocument();
});

it('shows measured upload bytes and ETA', () => {
  setup({ id: 1, state: 'push_running', push_progress: { done: 1048576, total: 4194304, eta: '30s' } });
  expect(screen.getByText('1.0 MiB / 4.0 MiB · 25% · ETA 30s')).toBeInTheDocument();
  expect(screen.getByRole('progressbar', { name: 'Upload progress' })).toHaveAttribute('aria-valuenow', '25');
});

it.each([null, { ...passed, status: 'unavailable' as const }, { ...passed, attempt: 'old' }])(
  'blocks upload without a current pass: %j',
  (validation) => {
    const { push } = setup({ ...prepared, validation });
    const button = screen.getByRole('button', { name: 'Upload to S3' });
    expect(button).toBeDisabled();
    expect(screen.getByText(/Validation must pass before upload/)).toBeInTheDocument();
    fireEvent.click(button);
    expect(push.mutate).not.toHaveBeenCalled();
  }
);

it('shows warnings and blocking issues separately', () => {
  setup({
    ...prepared,
    validation: {
      ...passed,
      status: 'failed',
      warnings: [{ message: 'Optional metadata missing' }],
      blocking_issues: [{ message: 'Invalid voxel spacing' }],
    },
  });
  expect(screen.getByText('Optional metadata missing')).toBeInTheDocument();
  expect(screen.getByText('Invalid voxel spacing')).toBeInTheDocument();
});

it('does not describe an unavailable result as a pass', () => {
  setup({ ...prepared, validation: { ...passed, status: 'unavailable' } });
  expect(screen.queryByText('Validation passed')).not.toBeInTheDocument();
  expect(screen.getByText('Validation unavailable')).toBeInTheDocument();
});

it('retries preparation and validation from a prepared job', () => {
  const { submit, push } = setup({ ...prepared, validation: null });
  fireEvent.click(screen.getByRole('button', { name: 'Prepare again' }));
  expect(submit.mutate).toHaveBeenCalledTimes(1);
  expect(push.mutate).not.toHaveBeenCalled();
});

it('renders grouped counts while keeping overall progress and ETA from the snapshot', () => {
  setup({
    id: 1,
    state: 'prep_running',
    sync_progress: {
      done: 10,
      total: 20,
      eta: '30s',
      items: [
        { label: 'Alignment', done: 2, total: 2 },
        { label: 'CTF', done: 2, total: 2 },
        { label: 'Tilt series', done: 0, total: 4 },
        { label: 'Tomograms', done: 3, total: 3 },
        { label: 'Metadata', done: 2, total: 4 },
        { label: 'Masks', done: 0, total: 1 },
        { label: 'Frames', done: 1, total: 4 },
      ],
    },
  });
  expect(screen.getAllByRole('listitem').map((row) => row.getAttribute('aria-label'))).toEqual([
    'Symlink tiltseries: 4 of 8, incomplete',
    'Symlink tomograms: 3 of 3, complete',
    'Other items: 3 of 9, incomplete',
  ]);
  expect(screen.queryByText('Deposit annotations')).not.toBeInTheDocument();
  expect(screen.queryByText('Alignment')).not.toBeInTheDocument();
  expect(screen.getByText('10 / 20 objects')).toBeInTheDocument();
  expect(screen.getAllByText('50% · ETA 30s')).toHaveLength(2);
  expect(screen.getByRole('progressbar', { name: 'Sync progress' })).toHaveAttribute('aria-valuenow', '50');
});

it('does not fetch or display logs for non-owners', () => {
  setLogs({ logs: 'private output', source: 'stored' });
  const dataset = { id: 1, title: 'DS', is_owner: false, job: { id: 1, state: 'failed' } } as Dataset;
  mockFlow.mockReturnValue({ submit: {}, push: {} });
  render(<SubmitStep dataset={dataset} readOnly reportSave={jest.fn()} />);
  expect(screen.getByText('Logs are visible to the submitter only.')).toBeVisible();
  expect(mockLogs).toHaveBeenCalledWith(1, expect.objectContaining({ enabled: false }));
  expect(screen.queryByText('private output')).not.toBeInTheDocument();
  expect(screen.getByRole('button', { name: 'Copy' })).toBeDisabled();
});
