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

it('resolves a valid ORCID to its owner name once the value is complete', async () => {
  mockValidate.mockResolvedValue({ label: 'Josiah Carberry' });
  render(<Harness kind="orcid" />);
  await userEvent.type(screen.getByLabelText('id'), '0000-0002-1825-0097');
  expect(await screen.findByText(/✓ Josiah Carberry/)).toBeInTheDocument();
});

it('shows not-found for an unresolvable DOI', async () => {
  mockValidate.mockResolvedValue(null);
  render(<Harness kind="doi" />);
  await userEvent.type(screen.getByLabelText('id'), '10.9999/nope');
  expect(await screen.findByText(/doi not found/i)).toBeInTheDocument();
});

it('does not block when the API is unreachable', async () => {
  mockValidate.mockRejectedValue(new Error('network'));
  render(<Harness kind="doi" />);
  await userEvent.type(screen.getByLabelText('id'), '10.1038/nature12373');
  expect(await screen.findByText(/lookup unavailable/i)).toBeInTheDocument();
});

it('resolves a valid ORCID pre-filled on mount (no interaction)', async () => {
  mockValidate.mockResolvedValue({ label: 'Josiah Carberry' });
  render(<Harness kind="orcid" initial="0000-0002-1825-0097" />);
  expect(await screen.findByText(/✓ Josiah Carberry/)).toBeInTheDocument();
});

it('resolves an EMPIAR related-DB entry', async () => {
  mockValidate.mockResolvedValue({ label: 'EMPIAR entry' });
  render(<Harness kind="related_db" />);
  await userEvent.type(screen.getByLabelText('id'), 'EMPIAR-10943');
  expect(await screen.findByText(/✓ EMPIAR entry/)).toBeInTheDocument();
});

it('flags an unrecognised related-DB format live', async () => {
  render(<Harness kind="related_db" />);
  await userEvent.type(screen.getByLabelText('id'), 'nonsense');
  expect(await screen.findByText(/EMPIAR-#####, EMD-####, or PDB-####/i)).toBeInTheDocument();
  expect(mockValidate).not.toHaveBeenCalled();
});
