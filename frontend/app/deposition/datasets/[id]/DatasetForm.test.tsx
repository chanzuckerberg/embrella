import '@testing-library/jest-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { act, fireEvent, render, screen } from '@testing-library/react';

import { DatasetForm } from './DatasetForm';
import * as api from '../../services/depositionApi';
import type { Dataset } from '../../types';

jest.mock('../../services/depositionApi', () => ({
  updateDataset: jest.fn(),
  fetchPeopleByIds: jest.fn().mockResolvedValue([]),
  searchPeople: jest.fn().mockResolvedValue([]),
  createPerson: jest.fn(),
}));

const updateDataset = api.updateDataset as jest.Mock;

const DRAFT = {
  id: 5,
  deposition: 1,
  dataset_id: 100,
  title: 'My dataset',
  status: 'draft',
  funding: [],
  authors_json: [
    { full_name: 'Test Author', affiliation: 'CZ Biohub', orcid: '0000-0002-1825-0097', is_corresponding: true, author_list_order: 0 },
  ],
} as unknown as Dataset;

function renderForm(dataset = DRAFT) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <DatasetForm dataset={dataset} />
    </QueryClientProvider>,
  );
}

describe('DatasetForm authors (#1003)', () => {
  beforeEach(() => updateDataset.mockResolvedValue({ ...DRAFT }));
  afterEach(() => jest.clearAllMocks());

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
