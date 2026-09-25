import '@testing-library/jest-dom';
import { type ComponentProps, useState } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import { Organism } from './Organism';
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

function renderOrganism(props: Partial<ComponentProps<typeof Organism>> = {}) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const onChangeOrganismName = jest.fn();
  const onChangeOrganismTaxid = jest.fn();
  function Controlled() {
    const [name, setName] = useState(props.organismName ?? '');
    const [taxid, setTaxid] = useState<number | null>(props.organismTaxid ?? null);
    return (
      <Organism
        {...props}
        organismName={name}
        organismTaxid={taxid}
        onChangeOrganismName={(value) => {
          setName(value);
          onChangeOrganismName(value);
        }}
        onChangeOrganismTaxid={(value) => {
          setTaxid(value);
          onChangeOrganismTaxid(value);
        }}
        readOnly={props.readOnly ?? false}
        innerRef={() => {}}
      />
    );
  }
  render(
    <QueryClientProvider client={client}>
      <Controlled />
    </QueryClientProvider>
  );
  return { onChangeOrganismName, onChangeOrganismTaxid };
}

it('resolves a set tax ID to its organism name', async () => {
  mockValidate.mockResolvedValue({ id: 'NCBITaxon:9606', label: 'Homo sapiens', synonyms: [] });
  renderOrganism({ organismTaxid: 9606 });
  expect(await screen.findByText(/Homo sapiens/i)).toBeInTheDocument();
});

it('flags a tax ID that cannot be resolved', async () => {
  mockValidate.mockResolvedValue(null);
  renderOrganism({ organismTaxid: 99999999 });
  expect(await screen.findByText(/tax id not found/i)).toBeInTheDocument();
});

it('does not block when OLS is unreachable', async () => {
  mockValidate.mockRejectedValue(new Error('network'));
  renderOrganism({ organismTaxid: 9606 });
  expect(await screen.findByText(/lookup unavailable/i)).toBeInTheDocument();
});

it('auto-fills name + numeric tax ID when a suggestion is picked', async () => {
  mockSearch.mockResolvedValue([{ id: 'NCBITaxon:9606', label: 'Homo sapiens', synonyms: [] }]);
  const { onChangeOrganismName, onChangeOrganismTaxid } = renderOrganism();

  const user = userEvent.setup();
  await user.type(screen.getByLabelText(/organism name/i), 'homo');
  const option = await screen.findByText(/Homo sapiens/);
  await user.click(option);

  await waitFor(() => expect(onChangeOrganismName).toHaveBeenCalledWith('Homo sapiens'));
  expect(onChangeOrganismTaxid).toHaveBeenCalledWith(9606);
});

it('fills an empty name from the resolved tax ID', async () => {
  mockValidate.mockResolvedValue({ id: 'NCBITaxon:9606', label: 'Homo sapiens', synonyms: [] });
  const { onChangeOrganismName } = renderOrganism({ organismName: '' });
  await userEvent.type(screen.getByLabelText(/NCBI tax ID/i), '9606');
  await waitFor(() => expect(screen.getByLabelText(/organism name/i)).toHaveValue('Homo sapiens'));
  expect(onChangeOrganismName).toHaveBeenCalledWith('Homo sapiens');
});

it('refreshes a previously auto-filled name when the tax ID changes', async () => {
  mockValidate.mockImplementation(async (id: string) => {
    if (id === 'NCBITaxon:9606') return { id, label: 'Homo sapiens', synonyms: [] };
    if (id === 'NCBITaxon:10090') return { id, label: 'Mus musculus', synonyms: [] };
    return null;
  });
  renderOrganism({ organismName: '' });
  const idField = screen.getByLabelText(/NCBI tax ID/i);
  await userEvent.type(idField, '9606');
  await waitFor(() => expect(screen.getByLabelText(/organism name/i)).toHaveValue('Homo sapiens'));
  await userEvent.clear(idField);
  await userEvent.type(idField, '10090');
  await waitFor(() => expect(screen.getByLabelText(/organism name/i)).toHaveValue('Mus musculus'));
});

it('does not overwrite an existing organism name when a tax ID is typed', async () => {
  // Guards against a partial tax ID (mid-typing) clobbering a name the user already has.
  mockValidate.mockResolvedValue({ id: 'NCBITaxon:9606', label: 'Homo sapiens', synonyms: [] });
  const { onChangeOrganismName } = renderOrganism({ organismName: 'Old organism' });
  await userEvent.type(screen.getByLabelText(/NCBI tax ID/i), '9606');
  await waitFor(() => expect(screen.getByLabelText(/NCBI tax ID/i)).toHaveValue('9606'));
  expect(onChangeOrganismName).not.toHaveBeenCalled();
  expect(screen.getByLabelText(/organism name/i)).toHaveValue('Old organism');
});

it('does not change a saved name in read-only mode', async () => {
  mockValidate.mockResolvedValue({ id: 'NCBITaxon:9606', label: 'Homo sapiens', synonyms: [] });
  const { onChangeOrganismName } = renderOrganism({ organismTaxid: 9606, readOnly: true });
  await screen.findByText('Homo sapiens');
  expect(onChangeOrganismName).not.toHaveBeenCalled();
});
