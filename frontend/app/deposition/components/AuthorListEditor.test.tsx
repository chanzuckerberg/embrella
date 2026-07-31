import '@testing-library/jest-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';

import { AuthorListEditor } from './AuthorListEditor';
import * as api from '../services/depositionApi';
import type { AuthorRef } from '../types';

jest.mock('../hooks/useDebounced', () => ({ useDebounced: (v: unknown) => v }));

jest.mock('../services/depositionApi', () => ({
  fetchPeopleByIds: jest.fn(),
  searchPeople: jest.fn().mockResolvedValue([]),
  createPerson: jest.fn(),
  updatePerson: jest.fn(),
  searchInstitutions: jest.fn(),
  createInstitution: jest.fn(),
}));

const fetchPeopleByIds = api.fetchPeopleByIds as jest.Mock;
const updatePerson = api.updatePerson as jest.Mock;
const searchInstitutions = api.searchInstitutions as jest.Mock;
const createInstitution = api.createInstitution as jest.Mock;

const PERSON = { id: 7, given_name: 'Ada', family_name: 'Lovelace', orcid: null, institution: null };
const AUTHORS: AuthorRef[] = [{ author_id: 7, is_primary: false, is_corresponding: false, author_list_order: 0 }];

function renderEditor(onChange: jest.Mock = jest.fn()) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={client}>
      <AuthorListEditor authors={AUTHORS} onChange={onChange} />
    </QueryClientProvider>
  );
  return { onChange };
}

beforeEach(() => {
  fetchPeopleByIds.mockResolvedValue([PERSON]);
  updatePerson.mockResolvedValue({});
  searchInstitutions.mockResolvedValue([]);
  createInstitution.mockResolvedValue({ id: 99, name: 'New Uni' });
});
afterEach(() => jest.clearAllMocks());

it('renders the author resolved from the People directory', async () => {
  renderEditor();
  expect(await screen.findByText('Ada Lovelace')).toBeInTheDocument();
});

it('toggling Primary in the edit panel flips the flag via onChange', async () => {
  const { onChange } = renderEditor();
  await screen.findByText('Ada Lovelace');

  fireEvent.click(screen.getByLabelText(/edit author 1/i));
  fireEvent.click(screen.getByLabelText('Primary author'));

  expect(onChange).toHaveBeenCalledWith([expect.objectContaining({ author_id: 7, is_primary: true })]);
});

it('saves a new affiliation as an Institution on Done (create + updatePerson with institution_id)', async () => {
  renderEditor();
  await screen.findByText('Ada Lovelace');

  fireEvent.click(screen.getByLabelText(/edit author 1/i));
  fireEvent.change(screen.getByLabelText('Affiliation'), { target: { value: 'New Uni' } });
  fireEvent.click(screen.getByLabelText(/done editing author 1/i));

  await waitFor(() => expect(updatePerson).toHaveBeenCalled());
  expect(searchInstitutions).toHaveBeenCalledWith('New Uni');
  expect(createInstitution).toHaveBeenCalledWith('New Uni');
  expect(updatePerson).toHaveBeenCalledWith(7, expect.objectContaining({ institution_id: 99 }));
});

it('reuses an existing institution instead of creating a duplicate', async () => {
  searchInstitutions.mockResolvedValue([{ id: 42, name: 'MIT' }]);
  renderEditor();
  await screen.findByText('Ada Lovelace');

  fireEvent.click(screen.getByLabelText(/edit author 1/i));
  fireEvent.change(screen.getByLabelText('Affiliation'), { target: { value: 'MIT' } });
  fireEvent.click(screen.getByLabelText(/done editing author 1/i));

  await waitFor(() => expect(updatePerson).toHaveBeenCalled());
  expect(createInstitution).not.toHaveBeenCalled();
  expect(updatePerson).toHaveBeenCalledWith(7, expect.objectContaining({ institution_id: 42 }));
});

it('removing an author calls onChange without it', async () => {
  const { onChange } = renderEditor();
  await screen.findByText('Ada Lovelace');

  fireEvent.click(screen.getByLabelText('Remove author 1'));
  expect(onChange).toHaveBeenCalledWith([]);
});

it('opens the Add author dialog', async () => {
  renderEditor();
  fireEvent.click(screen.getByRole('button', { name: /add author/i }));
  expect(await screen.findByRole('dialog')).toBeInTheDocument();
});
