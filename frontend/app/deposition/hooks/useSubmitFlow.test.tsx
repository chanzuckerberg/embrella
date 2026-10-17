import { act, fireEvent, render, renderHook, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';

import { useSubmitFlow } from './useSubmitFlow';
import * as api from '../services/depositionApi';
import { depositionKeys } from '../queryKeys';
import { SubmitStep } from '../wizard/steps/SubmitStep';
import type { Dataset } from '../types';

jest.mock('../services/depositionApi');

const dataset = {
  id: 7,
  deposition: 1,
  title: 'DS',
  status: 'syncing',
  job: {
    id: 1,
    state: 'prep_completed',
    prep_slurm_job_id: 'prep-1',
    validation: { status: 'passed', attempt: 'prep-1', warnings: [], blocking_issues: [] },
  },
} as Dataset;

function wrapperFor(client: QueryClient) {
  return function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
  };
}

function newClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false, staleTime: 5 * 60 * 1000 },
      mutations: { retry: false },
    },
  });
}

beforeEach(() => {
  jest.resetAllMocks();
  (api.fetchDataset as jest.Mock).mockResolvedValue(dataset);
  (api.fetchDatasetLogs as jest.Mock).mockResolvedValue({ logs: '', source: 'none' });
});

it('shows recovery after a failed upload, then starts preparation with the real hook', async () => {
  let serverDataset = dataset;
  (api.fetchDataset as jest.Mock).mockImplementation(async () => serverDataset);
  (api.pushDataset as jest.Mock).mockImplementation(async () => {
    serverDataset = {
      ...dataset,
      status: 'failed',
      job: { id: 1, state: 'failed', push_slurm_job_id: '99', error_message: 'Upload failed' },
    };
    throw new Error('Cluster launch failed');
  });
  (api.submitDataset as jest.Mock).mockImplementation(async () => {
    serverDataset = { ...dataset, job: { id: 1, state: 'prep_submitted' } };
    return { state: 'prep_submitted', dataset_status: 'syncing' };
  });
  const client = newClient();
  const { unmount } = render(<SubmitStep dataset={dataset} readOnly={false} reportSave={jest.fn()} />, {
    wrapper: wrapperFor(client),
  });

  fireEvent.click(screen.getByRole('button', { name: 'Submit deposition' }));
  const restart = await screen.findByRole('button', { name: 'Restart preparation' });
  expect(screen.getByText('Cluster launch failed')).toBeInTheDocument();
  expect(screen.queryByText('Upload failed')).toBeNull();
  expect(screen.getAllByRole('alert')).toHaveLength(1);
  expect(screen.queryByRole('button', { name: 'Submit deposition' })).not.toBeInTheDocument();
  fireEvent.click(restart);
  await waitFor(() => expect(api.submitDataset).toHaveBeenCalledWith(dataset.id));
  await waitFor(() => expect(screen.queryByRole('button', { name: 'Restart preparation' })).not.toBeInTheDocument());
  expect(screen.getByText('Waiting in queue')).toBeInTheDocument();
  expect(screen.queryByText('Cluster launch failed')).toBeNull();
  expect(api.pushDataset).toHaveBeenCalledTimes(1);
  unmount();
  client.clear();
});

it('shows upload completion and invalidates both cached submissions scopes', async () => {
  (api.pushDataset as jest.Mock).mockImplementation(async () => {
    (api.fetchDataset as jest.Mock).mockResolvedValue({
      ...dataset,
      status: 'pushed',
      job: { id: 1, state: 'completed', push_slurm_job_id: '99' },
    });
    return { state: 'push_submitted', dataset_status: 'syncing' };
  });
  const client = newClient();
  client.setQueryData(depositionKeys.submissions(), { submissions: [] });
  client.setQueryData(depositionKeys.submissions('mine'), { submissions: [] });
  const { unmount } = render(<SubmitStep dataset={dataset} readOnly={false} reportSave={jest.fn()} />, {
    wrapper: wrapperFor(client),
  });

  fireEvent.click(screen.getByRole('button', { name: 'Submit deposition' }));
  expect(
    await screen.findByText('Files have been uploaded to S3. Portal indexing and publication are separate steps.')
  ).toBeInTheDocument();
  expect(screen.queryByRole('button', { name: 'Submit deposition' })).not.toBeInTheDocument();
  expect(client.getQueryState(depositionKeys.submissions())?.isInvalidated).toBe(true);
  expect(client.getQueryState(depositionKeys.submissions('mine'))?.isInvalidated).toBe(true);
  unmount();
  client.clear();
});

it('uses an overridden polling interval and stops when the job finishes', async () => {
  jest.useFakeTimers();
  const initial = { ...dataset, job: { id: 1, state: 'prep_running' } } as Dataset;
  (api.fetchDataset as jest.Mock).mockResolvedValue({ ...dataset });
  const client = newClient();
  const { result, unmount } = renderHook(() => useSubmitFlow(initial, { pollIntervalMs: 50 }), {
    wrapper: wrapperFor(client),
  });
  try {
    await act(async () => {
      await jest.advanceTimersByTimeAsync(49);
    });
    expect(api.fetchDataset).not.toHaveBeenCalled();
    await act(async () => {
      await jest.advanceTimersByTimeAsync(1);
      await jest.advanceTimersByTimeAsync(1);
    });
    expect(result.current.dataset.job?.state).toBe('prep_completed');
    expect(api.fetchDataset).toHaveBeenCalledTimes(1);
    await act(async () => {
      await jest.advanceTimersByTimeAsync(200);
    });
    expect(api.fetchDataset).toHaveBeenCalledTimes(1);
  } finally {
    unmount();
    client.clear();
    jest.useRealTimers();
  }
});

it('refreshes the editable dataset before completing reset recovery', async () => {
  (api.resetDatasetPreparation as jest.Mock).mockImplementation(async () => {
    (api.fetchDataset as jest.Mock).mockResolvedValue({
      ...dataset,
      status: 'draft',
      job: { id: 1, state: 'pending', validation: null },
    });
  });
  const client = newClient();
  const { result, unmount } = renderHook(() => useSubmitFlow(dataset), { wrapper: wrapperFor(client) });
  await act(async () => {
    await result.current.resetPreparation.mutateAsync();
  });
  expect(api.resetDatasetPreparation).toHaveBeenCalledWith(dataset.id);
  await waitFor(() => expect(result.current.dataset.job?.state).toBe('pending'));
  expect(result.current.dataset.status).toBe('draft');
  unmount();
  client.clear();
});
