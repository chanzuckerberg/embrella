import '@testing-library/jest-dom';
import { fireEvent, render, screen } from '@testing-library/react';

import { SubmitStep } from './SubmitStep';
import { useSubmitFlow } from '../../hooks/useSubmitFlow';
import type { Dataset, DatasetJob } from '../../types';

jest.mock('../../hooks/useSubmitFlow', () => ({ useSubmitFlow: jest.fn() }));

const mockFlow = useSubmitFlow as jest.Mock;

function setup(job: DatasetJob | null, { readOnly = false } = {}) {
  const submit = { mutate: jest.fn(), isPending: false, error: null };
  const push = { mutate: jest.fn(), isPending: false, error: null };
  const dataset = { id: 1, title: 'DS', dataset_id: 2, status: 'draft', job } as Dataset;
  mockFlow.mockReturnValue({ dataset, submit, push });
  render(<SubmitStep dataset={dataset} readOnly={readOnly} reportSave={jest.fn()} />);
  return { submit, push };
}

beforeEach(() => jest.clearAllMocks());

it('submits for preparation when nothing has run', () => {
  const { submit } = setup(null);
  fireEvent.click(screen.getByRole('button', { name: /submit for preparation/i }));
  expect(submit.mutate).toHaveBeenCalled();
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

it('hides submit actions in read-only mode', () => {
  setup(null, { readOnly: true });
  expect(screen.queryByRole('button', { name: /submit/i })).toBeNull();
});
