import '@testing-library/jest-dom';
import { QueryClient, QueryClientProvider, useQuery } from '@tanstack/react-query';
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';

import { DatasetForm } from './DatasetForm';
import * as api from '../../services/depositionApi';
import type { Dataset } from '../../types';
import { depositionKeys } from '../../queryKeys';

jest.mock('../../services/depositionApi', () => ({
  updateDataset: jest.fn(),
  fetchDeposition: jest.fn(),
  fetchPeopleByIds: jest
    .fn()
    .mockResolvedValue([
      { id: 7, given_name: 'Test', family_name: 'Author', orcid: '0000-0002-1825-0097', institution: null },
    ]),
  searchPeople: jest.fn().mockResolvedValue([]),
  createPerson: jest.fn(),
  updatePerson: jest.fn(),
  searchInstitutions: jest.fn().mockResolvedValue([]),
  createInstitution: jest.fn(),
}));

const updateDataset = api.updateDataset as jest.Mock;

const DRAFT = {
  id: 5,
  deposition: 1,
  dataset_id: 100,
  title: 'My dataset',
  status: 'draft',
  metadata_issues: [],
  funding: [],
  authors_json: [{ author_id: 7, is_primary: true, is_corresponding: true, author_list_order: 0 }],
} as Dataset;

function renderForm(dataset = DRAFT, reportBlocking?: (count: number) => void) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  function ConnectedForm() {
    const { data } = useQuery({
      queryKey: depositionKeys.dataset(dataset.id),
      queryFn: async () => dataset,
      initialData: dataset,
      staleTime: Infinity,
    });
    return <DatasetForm dataset={data} readOnly={false} reportBlocking={reportBlocking} />;
  }
  return render(
    <QueryClientProvider client={client}>
      <ConnectedForm />
    </QueryClientProvider>
  );
}

beforeEach(() => {
  updateDataset.mockResolvedValue({ ...DRAFT });
  (api.fetchDeposition as jest.Mock).mockResolvedValue({ id: 1, authors_json: DRAFT.authors_json });
});
afterEach(() => jest.clearAllMocks());

describe('DatasetForm authors (#1003)', () => {
  it('shows the custom authors editor only when "Customize authors" is selected', () => {
    renderForm();
    // Default is "Same as deposition authors".
    expect(screen.queryByRole('button', { name: /add author/i })).not.toBeInTheDocument();

    fireEvent.click(screen.getByText('Customize authors'));
    expect(screen.getByRole('button', { name: /add author/i })).toBeInTheDocument();
  });

  it('includes authors_json in the save payload', async () => {
    jest.useFakeTimers();
    try {
      renderForm();
      fireEvent.change(screen.getByLabelText(/Title/), { target: { value: 'Edited title' } });
      await act(async () => {
        jest.advanceTimersByTime(6000);
      });
      expect(updateDataset).toHaveBeenCalled();
      const payload = updateDataset.mock.calls.at(-1)![1];
      expect(payload.authors_json).toEqual(DRAFT.authors_json);
      expect(payload).toHaveProperty('dataset_publications');
      expect(payload).toHaveProperty('related_database_entries');
    } finally {
      jest.useRealTimers();
    }
  });
});

it('distinguishes unknown authors from missing authors and allows retry after loading fails', async () => {
  let rejectAuthors!: (reason: Error) => void;
  (api.fetchDeposition as jest.Mock)
    .mockImplementationOnce(
      () =>
        new Promise((_, reject) => {
          rejectAuthors = reject;
        })
    )
    .mockResolvedValueOnce({ id: 1, authors_json: DRAFT.authors_json });
  const reportBlocking = jest.fn();
  renderForm(
    { ...DRAFT, description: 'Reviewed', sample: { sample_type: 'in_vitro' }, is_authors_same_as_deposition: true },
    reportBlocking
  );
  expect(screen.getByText('Loading deposition authors…')).toBeInTheDocument();
  expect(screen.queryByText(/Add at least one dataset author/)).not.toBeInTheDocument();
  expect(reportBlocking).toHaveBeenLastCalledWith(1);
  await act(async () => {
    rejectAuthors(new Error('Network unavailable'));
  });
  fireEvent.click(await screen.findByRole('button', { name: 'Retry' }));
  await waitFor(() => expect(reportBlocking).toHaveBeenLastCalledWith(0));
  expect(api.fetchDeposition).toHaveBeenCalledTimes(2);
  expect(screen.queryByText(/Could not load deposition authors/)).not.toBeInTheDocument();
});

it('displays backend issues and refreshes them after autosave without validating in the browser', async () => {
  jest.useFakeTimers();
  const reportBlocking = jest.fn();
  try {
    renderForm({ ...DRAFT, metadata_issues: ['Dataset title is required.'] }, reportBlocking);
    expect(screen.getByText('Dataset title is required.')).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText(/Title/), { target: { value: 'Saved title' } });
    expect(screen.getByText('Checking required fields after saving...')).toBeInTheDocument();
    await act(async () => {
      jest.advanceTimersByTime(6000);
    });
    expect(updateDataset).toHaveBeenCalled();
    await waitFor(() => expect(screen.queryByText('Dataset title is required.')).not.toBeInTheDocument());
    expect(reportBlocking).toHaveBeenLastCalledWith(0);
  } finally {
    jest.useRealTimers();
  }
});
