import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';

import { useDataset } from './useDataset';
import * as api from '../services/depositionApi';
import { depositionKeys } from '../queryKeys';
import { SubmitStep } from '../wizard/steps/SubmitStep';
import type { Dataset } from '../types';

jest.mock('../services/depositionApi');

const dataset = {
  id: 7,
  deposition: 1,
  metadata_issues: [],
  title: 'DS',
  status: 'syncing',
  job: {
    id: 1,
    state: 'prep_completed',
    prep_slurm_job_id: 'prep-1',
    validation: { status: 'passed', attempt: 'prep-1', warnings: [], blocking_issues: [] },
  },
} as Dataset;

function LiveSubmitStep() {
  const { data } = useDataset(dataset.id);
  return data ? <SubmitStep dataset={data} readOnly={false} reportSave={jest.fn()} /> : null;
}

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
  client.setQueryData(depositionKeys.dataset(dataset.id), dataset);
  client.setQueryData(depositionKeys.deposition(dataset.deposition), { datasets: [dataset] });
  const { unmount } = render(<LiveSubmitStep />, {
    wrapper: wrapperFor(client),
  });

  fireEvent.click(screen.getByRole('button', { name: 'Upload to S3' }));
  const restart = await screen.findByRole('button', { name: 'Restart preparation' });
  expect(screen.getByText('Cluster launch failed')).toBeInTheDocument();
  expect(screen.queryByText('Upload failed')).toBeNull();
  expect(screen.getAllByRole('alert')).toHaveLength(1);
  expect(screen.queryByRole('button', { name: 'Upload to S3' })).not.toBeInTheDocument();
  expect(client.getQueryState(depositionKeys.deposition(dataset.deposition))?.isInvalidated).toBe(true);
  client.setQueryData(depositionKeys.deposition(dataset.deposition), { datasets: [serverDataset] });
  fireEvent.click(restart);
  await waitFor(() => expect(api.submitDataset).toHaveBeenCalledWith(dataset.id));
  await waitFor(() => expect(screen.queryByRole('button', { name: 'Restart preparation' })).not.toBeInTheDocument());
  expect(screen.getByText('Waiting in queue')).toBeInTheDocument();
  expect(screen.queryByText('Cluster launch failed')).toBeNull();
  expect(client.getQueryState(depositionKeys.deposition(dataset.deposition))?.isInvalidated).toBe(true);
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
  client.setQueryData(depositionKeys.dataset(dataset.id), dataset);
  client.setQueryData(depositionKeys.deposition(dataset.deposition), { datasets: [dataset] });
  const { unmount } = render(<LiveSubmitStep />, {
    wrapper: wrapperFor(client),
  });

  fireEvent.click(screen.getByRole('button', { name: 'Upload to S3' }));
  expect(await screen.findByText('Files have been uploaded to S3.')).toBeInTheDocument();
  expect(screen.queryByRole('button', { name: 'Upload to S3' })).not.toBeInTheDocument();
  expect(client.getQueryState(depositionKeys.submissions())?.isInvalidated).toBe(true);
  expect(client.getQueryState(depositionKeys.submissions('mine'))?.isInvalidated).toBe(true);
  expect(client.getQueryState(depositionKeys.deposition(dataset.deposition))?.isInvalidated).toBe(true);
  unmount();
  client.clear();
});
