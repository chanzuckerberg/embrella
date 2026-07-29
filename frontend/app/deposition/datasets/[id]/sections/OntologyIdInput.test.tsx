import '@testing-library/jest-dom';
import type { ComponentProps } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';

import { OntologyIdInput } from './OntologyIdInput';
import { searchOntology, validateOntologyId } from '../../../services/ols';

jest.mock('../../../services/ols', () => ({
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
