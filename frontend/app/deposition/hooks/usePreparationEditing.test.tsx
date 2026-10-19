import { act, renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider, useQuery } from '@tanstack/react-query';
import type { ReactNode } from 'react';

import { usePreparationEditing } from './usePreparationEditing';
import { resetDatasetPreparation } from '../services/depositionApi';
import { depositionKeys } from '../queryKeys';
import type { Dataset } from '../types';

jest.mock('../services/depositionApi', () => ({ resetDatasetPreparation: jest.fn() }));
const resetApi = resetDatasetPreparation as jest.Mock;
const prepared = {
  id: 7,
  deposition: 1,
  title: 'My dataset',
  status: 'syncing',
  is_owner: true,
  job: {
    id: 1,
    state: 'prep_completed',
    prep_slurm_job_id: '123',
    validation: { status: 'failed', attempt: '123', warnings: [], blocking_issues: [{ message: 'Missing title' }] },
  },
} as Dataset;
const pendingJob = { id: 1, state: 'pending', validation: null };

function setup(dataset = prepared) {
  const client = new QueryClient({ defaultOptions: { mutations: { retry: false } } });
  client.setQueryData(depositionKeys.dataset(dataset.id), dataset);
  client.setQueryData(depositionKeys.deposition(dataset.deposition), { datasets: [dataset] });
  client.setQueryData(depositionKeys.submissions(), {});
  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={client}>{children}</QueryClientProvider>
  );
  const hook = renderHook(
    () => {
      const { data } = useQuery<Dataset>({
        queryKey: depositionKeys.dataset(dataset.id),
        queryFn: async () => dataset,
        enabled: false,
      });
      return usePreparationEditing(data);
    },
    { wrapper }
  );
  return { ...hook, client };
}

beforeEach(() => resetApi.mockReset().mockResolvedValue(pendingJob));

it('unlocks metadata only after reset clears the previous validation', async () => {
  let finish!: (job: typeof pendingJob) => void;
  resetApi.mockImplementationOnce(
    () =>
      new Promise((resolve) => {
        finish = resolve;
      })
  );
  const { result, client, unmount } = setup();
  expect(resetApi).not.toHaveBeenCalled();
  act(() => result.current.requestEdit());
  expect(result.current.dialogOpen).toBe(true);
  act(() => result.current.confirmEdit());
  await waitFor(() => expect(resetApi).toHaveBeenCalledTimes(1));
  expect(result.current.readOnly).toBe(true);
  expect(result.current.preparing).toBe(true);
  await act(async () => finish(pendingJob));
  await waitFor(() => expect(result.current.readOnly).toBe(false));
  expect(client.getQueryData<Dataset>(depositionKeys.dataset(7))).toMatchObject({ status: 'draft', job: pendingJob });
  expect(client.getQueryState(depositionKeys.submissions())?.isInvalidated).toBe(true);
  expect(client.getQueryState(depositionKeys.deposition(prepared.deposition))?.isInvalidated).toBe(true);
  unmount();
  client.clear();
});

it.each([
  { ...prepared, is_owner: false },
  { ...prepared, job: { id: 1, state: 'prep_running' } },
  { ...prepared, status: 'pushed', job: { id: 1, state: 'completed' } },
] as Dataset[])('keeps non-owned or in-flight/uploaded datasets locked ($job.state)', (dataset) => {
  const { result, client, unmount } = setup(dataset);
  expect(result.current.readOnly).toBe(true);
  expect(resetApi).not.toHaveBeenCalled();
  unmount();
  client.clear();
});

it('keeps edits locked after reset fails, exposes the error, and allows retry', async () => {
  resetApi.mockRejectedValueOnce(new Error('Cluster job still running'));
  const { result, client, unmount } = setup();
  act(() => result.current.confirmEdit());
  await waitFor(() => expect(result.current.error?.message).toBe('Cluster job still running'));
  expect(result.current.readOnly).toBe(true);
  expect(resetApi).toHaveBeenCalledTimes(1);
  await act(async () => result.current.confirmEdit());
  await waitFor(() => expect(result.current.readOnly).toBe(false));
  expect(resetApi).toHaveBeenCalledTimes(2);
  unmount();
  client.clear();
});
