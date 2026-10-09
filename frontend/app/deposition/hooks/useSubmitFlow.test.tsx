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
  title: 'DS',
  status: 'syncing',
  job: { id: 1, state: 'prep_completed' },
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
  expect(screen.getByText('Upload failed')).toBeInTheDocument();
  expect(screen.queryByRole('button', { name: 'Submit deposition' })).not.toBeInTheDocument();
  fireEvent.click(restart);
  await waitFor(() => expect(api.submitDataset).toHaveBeenCalledWith(dataset.id));
  await waitFor(() => expect(screen.queryByRole('button', { name: 'Restart preparation' })).not.toBeInTheDocument());
  expect(screen.getByText('In progress')).toBeInTheDocument();
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
  expect(await screen.findByText('Submitted — uploaded to the data portal.')).toBeInTheDocument();
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
