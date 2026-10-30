import { act, renderHook } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';

import { useDataset } from './useDataset';
import * as api from '../services/depositionApi';
import { depositionKeys } from '../queryKeys';
import type { Dataset } from '../types';

jest.mock('../services/depositionApi');

const dataset = {
  id: 7,
  deposition: 1,
  title: 'DS',
  status: 'syncing',
  job: { id: 1, state: 'prep_completed' },
} as Dataset;
function newClient() {
  return new QueryClient({ defaultOptions: { queries: { retry: false, staleTime: Infinity } } });
}
function wrapperFor(client: QueryClient) {
  return function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
  };
}

it.each(['prep', 'ingestion'])('polls active %s work and stops when it finishes or needs a retry', async (phase) => {
  jest.clearAllMocks();
  jest.useFakeTimers();
  const initial = {
    ...dataset,
    job:
      phase === 'prep'
        ? { id: 1, state: 'prep_running' }
        : { id: 1, state: 'completed', ingestion_state: 'not_started', ingestion_branch: 'deposition-1-dataset-2' },
  } as Dataset;
  const stopped = phase === 'prep' ? dataset : { ...initial, job: { ...initial.job, ingestion_retryable: true } };
  (api.fetchDataset as jest.Mock).mockResolvedValue(stopped);
  const client = newClient();
  client.setQueryData(depositionKeys.dataset(initial.id), initial);
  const { result, unmount } = renderHook(() => useDataset(initial.id), {
    wrapper: wrapperFor(client),
  });
  try {
    await act(async () => {
      await jest.advanceTimersByTimeAsync(3999);
    });
    expect(api.fetchDataset).not.toHaveBeenCalled();
    await act(async () => {
      await jest.advanceTimersByTimeAsync(1);
      await jest.advanceTimersByTimeAsync(1);
    });
    expect(result.current.data?.job).toEqual(stopped.job);
    expect(api.fetchDataset).toHaveBeenCalledTimes(1);
    await act(async () => {
      await jest.advanceTimersByTimeAsync(8000);
    });
    expect(api.fetchDataset).toHaveBeenCalledTimes(1);
  } finally {
    unmount();
    client.clear();
    jest.useRealTimers();
  }
});
