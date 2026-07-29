import '@testing-library/jest-dom';
import { useState } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import { IdentifierField } from './IdentifierField';
import { validateIdentifier } from '../services/identifiers';

jest.mock('../services/identifiers', () => {
  const actual = jest.requireActual('../services/identifiers');
  return { ...actual, validateIdentifier: jest.fn() };
});

const mockValidate = validateIdentifier as jest.Mock;

afterEach(() => jest.clearAllMocks());

function Harness({ kind, initial = '' }: { kind: 'orcid' | 'doi' | 'related_db'; initial?: string }) {
  const [v, setV] = useState(initial);
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return (
    <QueryClientProvider client={client}>
      <IdentifierField kind={kind} value={v} onChange={setV} label="id" />
    </QueryClientProvider>
  );
}

it('flags an invalid ORCID format live, before any lookup', async () => {
  render(<Harness kind="orcid" />);
  await userEvent.type(screen.getByLabelText('id'), '1234');
  expect(await screen.findByText(/invalid orcid format/i)).toBeInTheDocument();
  expect(mockValidate).not.toHaveBeenCalled();
});

it('resolves a valid ORCID to its owner name on blur', async () => {
  mockValidate.mockResolvedValue({ label: 'Josiah Carberry' });
  render(<Harness kind="orcid" />);
  const input = screen.getByLabelText('id');
  await userEvent.type(input, '0000-0002-1825-0097');
  await userEvent.tab(); // blur triggers the lookup
  expect(await screen.findByText(/✓ Josiah Carberry/)).toBeInTheDocument();
});

it('shows not-found for an unresolvable DOI on blur', async () => {
  mockValidate.mockResolvedValue(null);
  render(<Harness kind="doi" />);
  const input = screen.getByLabelText('id');
  await userEvent.type(input, '10.9999/nope');
  await userEvent.tab();
  expect(await screen.findByText(/doi not found/i)).toBeInTheDocument();
});

it('does not block when the API is unreachable', async () => {
  mockValidate.mockRejectedValue(new Error('network'));
  render(<Harness kind="doi" />);
  const input = screen.getByLabelText('id');
  await userEvent.type(input, '10.1038/nature12373');
  await userEvent.tab();
  expect(await screen.findByText(/lookup unavailable/i)).toBeInTheDocument();
});

it('resolves an EMPIAR related-DB entry on blur', async () => {
  mockValidate.mockResolvedValue({ label: 'EMPIAR entry' });
  render(<Harness kind="related_db" />);
  const input = screen.getByLabelText('id');
  await userEvent.type(input, 'EMPIAR-10943');
  await userEvent.tab();
  expect(await screen.findByText(/✓ EMPIAR entry/)).toBeInTheDocument();
});

it('flags an unrecognised related-DB format live', async () => {
  render(<Harness kind="related_db" />);
  await userEvent.type(screen.getByLabelText('id'), 'nonsense');
  expect(await screen.findByText(/EMPIAR-#####, EMD-####, or PDB-####/i)).toBeInTheDocument();
  expect(mockValidate).not.toHaveBeenCalled();
});
