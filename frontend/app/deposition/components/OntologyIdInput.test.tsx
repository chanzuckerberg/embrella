import '@testing-library/jest-dom';
import { type ComponentProps, useState } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';

import { OntologyIdInput } from './OntologyIdInput';
import { searchOntology, validateOntologyId } from '../services/ols';

jest.mock('../services/ols', () => ({
  searchOntology: jest.fn(),
  validateOntologyId: jest.fn(),
}));

const mockSearch = searchOntology as jest.Mock;
const mockValidate = validateOntologyId as jest.Mock;

beforeEach(() => {
  mockSearch.mockResolvedValue([]);
  mockValidate.mockResolvedValue(null);
});
afterEach(() => jest.clearAllMocks());

function renderInput(props: Partial<ComponentProps<typeof OntologyIdInput>> = {}) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <OntologyIdInput
        label="Assay"
        ontology="efo"
        pattern="^EFO:[0-9]{7}$"
        prefix="EFO"
        lookup="https://example.org"
        name=""
        id=""
        onChange={() => {}}
        {...props}
      />
    </QueryClientProvider>
  );
}

const CL = { ontology: 'cl', pattern: '^CL:[0-9]{7}$', prefix: 'CL', label: 'Cell type' } as const;
const CELL_TYPE = {
  ontology: 'cl,uberon,fbbt,wbbt,zfa',
  pattern: '(^CL:[0-9]{7}$)|(WBbt:[0-9]{7}$)|(ZFA:[0-9]{7}$)|(FBbt:[0-9]{8}$)|(^UBERON:[0-9]{7}$)',
  prefix: 'CL',
  label: 'Cell type',
} as const;

it('flags an id that does not match the field pattern (wrong ontology)', async () => {
  renderInput({ id: 'UBERON:0000955' }); // valid UBERON id, invalid for an EFO field
  expect(await screen.findByText(/invalid id format for this field/i)).toBeInTheDocument();
});

it('manualOnly field: format-validates a registry id and never calls OLS', async () => {
  renderInput({
    ontology: '',
    pattern: '(WBStrain[0-9]{8}$)|(^NCBITaxon:[0-9]+$)|(^CVCL_[A-Z0-9]{4,}$)|(^CC-[0-9]{4}$)',
    manualOnly: true,
    idPlaceholder: 'e.g. CVCL_1234',
    id: 'CVCL_1234',
  });
  expect(await screen.findByText(/^valid format$/i)).toBeInTheDocument();
  expect(mockValidate).not.toHaveBeenCalled();
  expect(mockSearch).not.toHaveBeenCalled();
});

it('resolves a valid OLS id to its label', async () => {
  mockValidate.mockResolvedValue({ id: 'CL:0000540', label: 'neuron', synonyms: [] });
  renderInput({ ...CL, id: 'CL:0000540' });
  expect(await screen.findByText(/neuron/i)).toBeInTheDocument();
});

it('flags a well-formed id OLS cannot resolve', async () => {
  mockValidate.mockResolvedValue(null);
  renderInput({ ...CL, id: 'CL:9999999' });
  expect(await screen.findByText(/id not found/i)).toBeInTheDocument();
});

it('does not block when OLS is unreachable (lookup error)', async () => {
  mockValidate.mockRejectedValue(new Error('network'));
  renderInput({ ...CL, id: 'CL:0000540' });
  expect(await screen.findByText(/valid format \(lookup unavailable\)/i)).toBeInTheDocument();
});

it('accepts a UBERON id in the multi-ontology Cell type field', async () => {
  mockValidate.mockResolvedValue({ id: 'UBERON:0000955', label: 'brain', synonyms: [] });
  renderInput({ ...CELL_TYPE, id: 'UBERON:0000955' });
  expect(await screen.findByText(/brain/i)).toBeInTheDocument();
});

it('restricts GO cell-component suggestions to the Cellular Component branch', async () => {
  renderInput({
    ontology: 'go',
    pattern: '^GO:[0-9]{7}$',
    prefix: 'GO',
    label: 'Cell component',
    childrenOf: 'http://purl.obolibrary.org/obo/GO_0005575',
    name: 'mitochondrion',
  });
  await waitFor(() =>
    expect(mockSearch).toHaveBeenCalledWith('mitochondrion', 'go', 'http://purl.obolibrary.org/obo/GO_0005575')
  );
});

it('does not scope suggestions for a field with no branch restriction', async () => {
  renderInput({ ...CL, name: 'neuron' });
  await waitFor(() => expect(mockSearch).toHaveBeenCalledWith('neuron', 'cl', undefined));
});

it('prefixInValue=false: shows the bare identifier and stores it fully-qualified', () => {
  const onChange = jest.fn();
  renderInput({
    label: 'Object',
    prefix: 'UniProtKB',
    ontology: '',
    manualOnly: true,
    pattern: '^UniProtKB:.+$',
    prefixInValue: false,
    id: 'UniProtKB:P31224',
    onChange,
  });
  const input = screen.getByLabelText(/Object ID/);
  expect(input).toHaveValue('P31224');
  fireEvent.change(input, { target: { value: 'P0A6G7' } });
  expect(onChange).toHaveBeenCalledWith({ id: 'UniProtKB:P0A6G7' });
});

it('clears the paired ID when the ontology name is cleared via the X', () => {
  const onChange = jest.fn();
  renderInput({ ...CL, name: 'neuron', id: 'CL:0000540', onChange });
  fireEvent.click(screen.getByTitle('Clear'));
  expect(onChange).toHaveBeenCalledWith({ name: '', id: '' });
});

it('prefixInValue=false: clearing the input stores empty, not a lone prefix', () => {
  const onChange = jest.fn();
  renderInput({
    label: 'Object',
    prefix: 'UniProtKB',
    ontology: '',
    manualOnly: true,
    pattern: '^UniProtKB:.+$',
    prefixInValue: false,
    id: 'UniProtKB:P31224',
    onChange,
  });
  fireEvent.change(screen.getByLabelText(/Object ID/), { target: { value: '' } });
  expect(onChange).toHaveBeenCalledWith({ id: '' });
});

it('backfills an empty name from an exact ID lookup', async () => {
  mockValidate.mockResolvedValue({ id: 'CL:0000540', label: 'neuron', synonyms: [] });
  const onChange = jest.fn();
  renderInput({ ...CL, id: 'CL:0000540', onChange });
  await waitFor(() => expect(onChange).toHaveBeenCalledWith({ name: 'neuron' }));
});

it('does not replace an existing name just by loading the field', async () => {
  mockValidate.mockResolvedValue({ id: 'CL:0000540', label: 'neuron', synonyms: [] });
  const onChange = jest.fn();
  renderInput({ ...CL, id: 'CL:0000540', name: 'Saved label', onChange });
  await screen.findByText('neuron');
  expect(onChange).not.toHaveBeenCalled();
});

it('does not write lookup results into read-only metadata', async () => {
  mockValidate.mockResolvedValue({ id: 'CL:0000540', label: 'neuron', synonyms: [] });
  const onChange = jest.fn();
  renderInput({ ...CL, id: 'CL:0000540', disabled: true, onChange });
  await screen.findByText('neuron');
  expect(onChange).not.toHaveBeenCalled();
});

it('fills an existing name when a different ID is entered', async () => {
  mockValidate.mockImplementation(async (id: string) =>
    id === 'CL:0000540' ? { id, label: 'neuron', synonyms: [] } : null
  );
  function Controlled() {
    const [pair, setPair] = useState({ name: 'Previous name', id: '' });
    return (
      <OntologyIdInput
        {...CL}
        lookup="https://example.org"
        {...pair}
        onChange={(patch) => setPair((previous) => ({ ...previous, ...patch }))}
      />
    );
  }
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={client}>
      <Controlled />
    </QueryClientProvider>
  );
  fireEvent.change(screen.getByLabelText(/Cell type ID/), { target: { value: 'CL:0000540' } });
  await waitFor(() => expect(screen.getByLabelText(/Cell type name/)).toHaveValue('neuron'));
});

it('does not apply a late result after the user starts a new name search', async () => {
  let finish!: (term: { id: string; label: string; synonyms: string[] }) => void;
  mockValidate.mockImplementation(
    () =>
      new Promise((resolve) => {
        finish = resolve;
      })
  );
  function Controlled() {
    const [pair, setPair] = useState({ name: '', id: 'CL:0000540' });
    return (
      <OntologyIdInput
        {...CL}
        lookup="https://example.org"
        {...pair}
        onChange={(patch) => setPair((previous) => ({ ...previous, ...patch }))}
      />
    );
  }
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={client}>
      <Controlled />
    </QueryClientProvider>
  );
  await waitFor(() => expect(mockValidate).toHaveBeenCalled());
  fireEvent.change(screen.getByLabelText(/Cell type name/), { target: { value: 'New search' } });
  finish({ id: 'CL:0000540', label: 'neuron', synonyms: [] });
  await waitFor(() => expect(client.isFetching()).toBe(0));
  expect(screen.getByLabelText(/Cell type name/)).toHaveValue('New search');
  expect(screen.getByLabelText(/Cell type ID/)).toHaveValue('');
});
