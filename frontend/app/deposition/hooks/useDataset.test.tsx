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

it('polls active jobs every four seconds and stops when preparation finishes', async () => {
  jest.useFakeTimers();
  const initial = { ...dataset, job: { id: 1, state: 'prep_running' } } as Dataset;
  (api.fetchDataset as jest.Mock).mockResolvedValue({ ...dataset });
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
    expect(result.current.data?.job?.state).toBe('prep_completed');
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
