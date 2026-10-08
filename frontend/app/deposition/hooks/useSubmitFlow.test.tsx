import { act, renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';

import { useSubmitFlow } from './useSubmitFlow';
import * as api from '../services/depositionApi';
import type { Dataset } from '../types';

jest.mock('../services/depositionApi');

const dataset = { id: 7, title: 'DS', status: 'draft' } as Dataset;

function wrapperFor(client: QueryClient) {
  return function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
  };
}

function newClient() {
  return new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
}

beforeEach(() => {
  jest.clearAllMocks();
  (api.fetchDataset as jest.Mock).mockResolvedValue(dataset);
});

it('refetches the dataset after a FAILED push, so the server-recorded failure surfaces', async () => {
  // start_push records `failed` before the view returns 502; without a refetch the client
  // would keep showing prep_completed and leave Submit deposition enabled.
  (api.pushDataset as jest.Mock).mockRejectedValue(new Error('502'));
  const client = newClient();
  const invalidate = jest.spyOn(client, 'invalidateQueries');

  const { result } = renderHook(() => useSubmitFlow(dataset), { wrapper: wrapperFor(client) });
  await act(async () => {
    await result.current.push.mutateAsync().catch(() => undefined);
  });

  // refresh() invalidates the dataset + submissions list — proving it ran on error, not only success.
  await waitFor(() => expect(invalidate).toHaveBeenCalledTimes(2));
  // The submissions invalidation must use the scope-agnostic prefix so 'mine' refreshes too.
  expect(invalidate).toHaveBeenCalledWith({ queryKey: ['depositions', 'submissions'] });
});

it('still refetches after a successful push', async () => {
  (api.pushDataset as jest.Mock).mockResolvedValue({ state: 'push_submitted', dataset_status: 'syncing' });
  const client = newClient();
  const invalidate = jest.spyOn(client, 'invalidateQueries');

  const { result } = renderHook(() => useSubmitFlow(dataset), { wrapper: wrapperFor(client) });
  await act(async () => {
    await result.current.push.mutateAsync();
  });

  await waitFor(() => expect(invalidate).toHaveBeenCalledTimes(2));
});
