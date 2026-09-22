import '@testing-library/jest-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import { AddAuthorDialog } from './AddAuthorDialog';

jest.mock('../services/depositionApi', () => ({
  searchPeople: jest.fn().mockResolvedValue([]),
  createPerson: jest.fn(),
}));

function renderDialog() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={client}>
      <AddAuthorDialog open onClose={jest.fn()} existingIds={[]} onAdd={jest.fn()} />
    </QueryClientProvider>
  );
}

afterEach(() => jest.clearAllMocks());

it('clears a typed-but-unselected author query via the clear button', async () => {
  renderDialog();
  const input = screen.getByPlaceholderText('Search people…');

  await userEvent.type(input, 'ada');
  expect(input).toHaveValue('ada');

  await userEvent.click(screen.getByLabelText('Clear search'));
  expect(input).toHaveValue('');
});

it('does not show the clear button when the query is empty', () => {
  renderDialog();
  expect(screen.queryByLabelText('Clear search')).not.toBeInTheDocument();
});
