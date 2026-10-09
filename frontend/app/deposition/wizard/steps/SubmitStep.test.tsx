import '@testing-library/jest-dom';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';

import { SubmitStep } from './SubmitStep';
import { useSubmitFlow } from '../../hooks/useSubmitFlow';
import { checkSshSetup } from '../../services/depositionApi';
import type { Dataset, DatasetJob } from '../../types';

jest.mock('../../hooks/useSubmitFlow', () => ({ useSubmitFlow: jest.fn() }));
jest.mock('../../services/depositionApi', () => ({
  ...jest.requireActual('../../services/depositionApi'),
  checkSshSetup: jest.fn().mockResolvedValue({ username: 'alice' }),
}));
// Stub the modal with a button that fires onSuccess, so we can assert the post-setup retry.
jest.mock('@app/common/components/SSHSetupModal', () => ({
  SSHSetupModal: ({ onSuccess }: { onSuccess: () => void }) => (
    <button type="button" onClick={onSuccess}>
      confirm-ssh
    </button>
  ),
}));

const sshError = () => Object.assign(new Error('ssh not set up'), { sshSetupRequired: true, clusterId: 'czii' });

const mockFlow = useSubmitFlow as jest.Mock;
const mockCheckSsh = checkSshSetup as jest.Mock;

function setup(job: DatasetJob | null, { readOnly = false } = {}) {
  const submit = { mutate: jest.fn(), reset: jest.fn(), isPending: false, isError: false, error: null };
  const push = { mutate: jest.fn(), reset: jest.fn(), isPending: false, isError: false, error: null };
  const dataset = { id: 1, title: 'DS', dataset_id: 2, status: 'draft', job } as Dataset;
  mockFlow.mockReturnValue({ dataset, submit, push });
  render(<SubmitStep dataset={dataset} readOnly={readOnly} reportSave={jest.fn()} />);
  return { submit, push };
}

beforeEach(() => jest.clearAllMocks());

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

it('opens the SSH setup modal on a 403 and keeps it out of the error banner', async () => {
  const err = sshError();
  const submit = {
    mutate: jest.fn((_v, opts) => opts?.onError?.(err)),
    reset: jest.fn(),
    isPending: false,
    isError: true,
    error: err,
  };
  const push = { mutate: jest.fn(), reset: jest.fn(), isPending: false, isError: false, error: null };
  const dataset = { id: 1, title: 'DS', dataset_id: 2, status: 'draft', job: null } as Dataset;
  mockFlow.mockReturnValue({ dataset, submit, push });
  render(<SubmitStep dataset={dataset} readOnly={false} reportSave={jest.fn()} />);

  // Auto-start hits the 403 → resolve the cluster username → open the shared setup modal.
  await waitFor(() => expect(mockCheckSsh).toHaveBeenCalledWith('czii'));
  // The SSH error is handled by the modal, not duplicated in the error banner.
  expect(screen.queryByText('ssh not set up')).toBeNull();
});

it('retries prep (not push) after SSH setup for a prep launch', async () => {
  const err = sshError();
  let calls = 0;
  const submit = {
    mutate: jest.fn((_v, opts) => {
      calls += 1;
      if (calls === 1) opts?.onError?.(err); // only the first (auto-start) launch is rejected
    }),
    reset: jest.fn(),
    isPending: false,
    isError: true,
    error: err,
  };
  const push = { mutate: jest.fn(), reset: jest.fn(), isPending: false, isError: false, error: null };
  const dataset = { id: 1, title: 'DS', dataset_id: 2, status: 'draft', job: null } as Dataset;
  mockFlow.mockReturnValue({ dataset, submit, push });
  render(<SubmitStep dataset={dataset} readOnly={false} reportSave={jest.fn()} />);

  fireEvent.click(await screen.findByText('confirm-ssh'));
  expect(submit.mutate).toHaveBeenCalledTimes(2);
  expect(push.mutate).not.toHaveBeenCalled();
});

it('retries push (not prep) after SSH setup for a push launch', async () => {
  const err = sshError();
  let pushCalls = 0;
  const submit = { mutate: jest.fn(), reset: jest.fn(), isPending: false, isError: false, error: null };
  const push = {
    mutate: jest.fn((_v, opts) => {
      pushCalls += 1;
      if (pushCalls === 1) opts?.onError?.(err);
    }),
    reset: jest.fn(),
    isPending: false,
    isError: true,
    error: err,
  };
  const dataset = {
    id: 1,
    title: 'DS',
    dataset_id: 2,
    status: 'draft',
    job: { id: 1, state: 'prep_completed' },
  } as Dataset;
  mockFlow.mockReturnValue({ dataset, submit, push });
  render(<SubmitStep dataset={dataset} readOnly={false} reportSave={jest.fn()} />);

  fireEvent.click(screen.getByRole('button', { name: /submit deposition/i }));
  fireEvent.click(await screen.findByText('confirm-ssh'));
  expect(push.mutate).toHaveBeenCalledTimes(2);
  expect(submit.mutate).not.toHaveBeenCalled();
});

it('recovers a failed push by restarting prep, not re-pushing', () => {
  const { submit, push } = setup({ id: 1, state: 'failed', push_slurm_job_id: '99', error_message: 'upload died' });
  const retry = screen.getByRole('button', { name: /restart preparation/i });
  expect(screen.queryByRole('button', { name: /retry upload/i })).toBeNull();
  fireEvent.click(retry);
  expect(submit.mutate).toHaveBeenCalled();
  expect(push.mutate).not.toHaveBeenCalled();
});
