import '@testing-library/jest-dom';
import { fireEvent, render, screen } from '@testing-library/react';

import { SubmitStep } from './SubmitStep';
import { useSubmitFlow } from '../../hooks/useSubmitFlow';
import type { Dataset, DatasetJob } from '../../types';

jest.mock('../../hooks/useSubmitFlow', () => ({ useSubmitFlow: jest.fn() }));

const mockFlow = useSubmitFlow as jest.Mock;

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

it('recovers a failed push by restarting prep, not re-pushing', () => {
  const { submit, push } = setup({ id: 1, state: 'failed', push_slurm_job_id: '99', error_message: 'upload died' });
  const retry = screen.getByRole('button', { name: /restart preparation/i });
  expect(screen.queryByRole('button', { name: /retry upload/i })).toBeNull();
  fireEvent.click(retry);
  expect(submit.mutate).toHaveBeenCalled();
  expect(push.mutate).not.toHaveBeenCalled();
});
