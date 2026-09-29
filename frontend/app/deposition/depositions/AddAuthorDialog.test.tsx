import '@testing-library/jest-dom';
import { useState } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import { AddAuthorDialog } from './AddAuthorDialog';
import { createPerson, searchPeople } from '../services/depositionApi';

jest.mock('../services/depositionApi', () => ({
  searchPeople: jest.fn().mockResolvedValue([]),
  createPerson: jest.fn(),
}));

const mockSearch = searchPeople as jest.Mock;
const mockCreate = createPerson as jest.Mock;
afterEach(() => jest.clearAllMocks());

function renderDialog() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={client}>
      <AddAuthorDialog open onClose={jest.fn()} existingIds={[]} onAdd={jest.fn()} />
    </QueryClientProvider>
  );
}

function Harness() {
  const [open, setOpen] = useState(true);
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return (
    <QueryClientProvider client={client}>
      <button onClick={() => setOpen(true)}>reopen</button>
      <AddAuthorDialog open={open} onClose={() => setOpen(false)} existingIds={[]} onAdd={jest.fn()} />
    </QueryClientProvider>
  );
}

it('opens on directory search with the new-author path behind a link (not a visible form)', () => {
  renderDialog();
  expect(screen.getByPlaceholderText(/search by name/i)).toBeInTheDocument();
  expect(screen.queryByLabelText(/Given name/)).not.toBeInTheDocument();
  expect(screen.getByRole('button', { name: /add a new author/i })).toBeInTheDocument();
});

it('switches to the new-author form and back to search', async () => {
  renderDialog();
  await userEvent.click(screen.getByRole('button', { name: /add a new author/i }));
  expect(screen.getByLabelText(/Given name/)).toBeInTheDocument();
  expect(screen.queryByPlaceholderText(/search by name/i)).not.toBeInTheDocument();
  await userEvent.click(screen.getByRole('button', { name: /back to directory/i }));
  expect(screen.getByPlaceholderText(/search by name/i)).toBeInTheDocument();
  expect(screen.queryByLabelText(/Given name/)).not.toBeInTheDocument();
});

it('shows a selected-author card with Change after picking from the directory', async () => {
  mockSearch.mockResolvedValue([{ id: 7, given_name: 'Ada', family_name: 'Lovelace', orcid: null }]);
  renderDialog();
  await userEvent.type(screen.getByPlaceholderText(/search by name/i), 'ada');
  await userEvent.click(await screen.findByRole('option', { name: /Ada Lovelace/i }));

  expect(screen.getByRole('button', { name: /change/i })).toBeInTheDocument();
  expect(screen.queryByRole('button', { name: /add a new author/i })).not.toBeInTheDocument();

  await userEvent.click(screen.getByRole('button', { name: /change/i }));
  expect(screen.getByPlaceholderText(/search by name/i)).toBeInTheDocument();
});

it('clears a typed directory query via the clear button', async () => {
  renderDialog();
  const input = screen.getByPlaceholderText(/search by name/i);
  await userEvent.type(input, 'ada');
  expect(input).toHaveValue('ada');
  await userEvent.click(screen.getByLabelText('Clear search'));
  expect(input).toHaveValue('');
});

it('enables Add only once a directory author is picked', async () => {
  mockSearch.mockResolvedValue([{ id: 7, given_name: 'Ada', family_name: 'Lovelace', orcid: null }]);
  renderDialog();
  expect(screen.getByRole('button', { name: 'Add' })).toBeDisabled();
  await userEvent.type(screen.getByPlaceholderText(/search by name/i), 'ada');
  await userEvent.click(await screen.findByRole('option', { name: /Ada Lovelace/i }));
  expect(screen.getByRole('button', { name: 'Add' })).toBeEnabled();
});

it('enables Add in the new-author form once name fields are filled', async () => {
  renderDialog();
  await userEvent.click(screen.getByRole('button', { name: /add a new author/i }));
  expect(screen.getByRole('button', { name: 'Add' })).toBeDisabled();
  await userEvent.type(screen.getByLabelText(/Given name/), 'Ada');
  await userEvent.type(screen.getByLabelText(/Family name/), 'Lovelace');
  expect(screen.getByRole('button', { name: 'Add' })).toBeEnabled();
});

it('resets to directory search (no stale create form) when reopened', async () => {
  render(<Harness />);
  await userEvent.click(screen.getByRole('button', { name: /add a new author/i }));
  await userEvent.type(screen.getByLabelText(/Given name/), 'Ada');
  await userEvent.click(screen.getByRole('button', { name: /cancel/i }));
  // Dialog exit transition un-hides the background; wait for the reopen button to be reachable.
  await userEvent.click(await screen.findByRole('button', { name: /reopen/i }));
  expect(screen.getByPlaceholderText(/search by name/i)).toBeInTheDocument();
  expect(screen.queryByLabelText(/Given name/)).not.toBeInTheDocument();
});

it('disables the back link while the new author is being created', async () => {
  mockCreate.mockReturnValue(new Promise(() => {})); // never resolves - stays pending
  renderDialog();
  await userEvent.click(screen.getByRole('button', { name: /add a new author/i }));
  await userEvent.type(screen.getByLabelText(/Given name/), 'Ada');
  await userEvent.type(screen.getByLabelText(/Family name/), 'Lovelace');
  await userEvent.click(screen.getByRole('button', { name: 'Add' }));
  expect(screen.getByRole('button', { name: /back to directory/i })).toBeDisabled();
});
