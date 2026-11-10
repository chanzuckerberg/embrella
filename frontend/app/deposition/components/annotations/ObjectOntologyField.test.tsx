import '@testing-library/jest-dom';
import { type ComponentProps, useState } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import { ObjectOntologyField } from './ObjectOntologyField';
import { searchOntology, validateOntologyId } from '../../services/ols';
import type { DepositionAnnotation } from '../../types';

jest.mock('../../services/ols', () => ({
  searchOntology: jest.fn(),
  validateOntologyId: jest.fn(),
  GO_CELLULAR_COMPONENT_IRI: 'http://purl.obolibrary.org/obo/GO_0005575',
}));
// Skip the real debounce wait; typing stays character-by-character, only the 300ms delay is removed.
jest.mock('../../hooks/useDebounced', () => ({ useDebounced: (value: unknown) => value }));

const mockSearch = searchOntology as jest.Mock;
const mockValidate = validateOntologyId as jest.Mock;

beforeEach(() => {
  mockSearch.mockResolvedValue([]);
  mockValidate.mockResolvedValue(null);
});
afterEach(() => jest.clearAllMocks());

function renderField(props: Partial<ComponentProps<typeof ObjectOntologyField>> = {}) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const onChange = jest.fn();
  render(
    <QueryClientProvider client={client}>
      <ObjectOntologyField name="" id="" onChange={onChange} {...props} />
    </QueryClientProvider>
  );
  return { onChange };
}

function renderControlled(initial: Pick<DepositionAnnotation, 'object_name' | 'object_id'>) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  function Controlled() {
    const [pair, setPair] = useState(initial);
    return (
      <ObjectOntologyField
        name={pair.object_name ?? ''}
        id={pair.object_id ?? ''}
        onChange={(patch) => setPair((prev) => ({ ...prev, ...patch }))}
      />
    );
  }
  render(
    <QueryClientProvider client={client}>
      <Controlled />
    </QueryClientProvider>
  );
}

it('backfills an empty object name from a resolvable ID', async () => {
  mockValidate.mockResolvedValue({ id: 'GO:0005886', label: 'plasma membrane', synonyms: [] });
  const { onChange } = renderField({ id: 'GO:0005886' });
  await waitFor(() => expect(onChange).toHaveBeenCalledWith({ object_name: 'plasma membrane' }));
});

it('does not overwrite an existing object name (e.g. imported from copick)', async () => {
  mockValidate.mockResolvedValue({ id: 'GO:0005886', label: 'plasma membrane', synonyms: [] });
  const { onChange } = renderField({ id: 'GO:0005886', name: 'membrane (copick)' });
  await screen.findByText(/plasma membrane/i); // the resolved label shows in the helper text
  expect(onChange).not.toHaveBeenCalled();
});

it('does not write into a disabled field', async () => {
  mockValidate.mockResolvedValue({ id: 'GO:0005886', label: 'plasma membrane', synonyms: [] });
  const { onChange } = renderField({ id: 'GO:0005886', disabled: true });
  await screen.findByText(/plasma membrane/i);
  expect(onChange).not.toHaveBeenCalled();
});

it('clearing the object name also clears the ID and does not snap the name back', async () => {
  mockValidate.mockResolvedValue({ id: 'GO:0005886', label: 'plasma membrane', synonyms: [] });
  const onChangeSpy = jest.fn();
  function Controlled() {
    const [pair, setPair] = useState({ object_name: '', object_id: 'GO:0005886' });
    return (
      <ObjectOntologyField
        name={pair.object_name}
        id={pair.object_id}
        onChange={(patch) => {
          onChangeSpy(patch);
          setPair((previous) => ({
            object_name: patch.object_name ?? previous.object_name,
            object_id: patch.object_id ?? previous.object_id,
          }));
        }}
      />
    );
  }
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={client}>
      <Controlled />
    </QueryClientProvider>
  );
  // The resolvable ID backfills the empty name first.
  await waitFor(() => expect(screen.getByLabelText(/object name/i)).toHaveValue('plasma membrane'));
  await userEvent.clear(screen.getByLabelText(/object name/i));
  // Clearing the name drops the ID too, so the effect can't restore the label.
  expect(onChangeSpy).toHaveBeenCalledWith({ object_name: '', object_id: '' });
  await waitFor(() => expect(screen.getByLabelText(/object name/i)).toHaveValue(''));
  expect(screen.getByLabelText(/object id/i)).toHaveValue('');
});

it('scopes GO object search to the cellular component branch (after picking GO)', async () => {
  renderField();
  fireEvent.mouseDown(screen.getByRole('combobox', { name: /Ontology/ }));
  fireEvent.click(screen.getByRole('option', { name: /^GO/ }));
  await userEvent.type(screen.getByLabelText(/Object ID/), 'ribosome');
  await waitFor(() =>
    expect(mockSearch).toHaveBeenCalledWith('ribosome', 'go', 'http://purl.obolibrary.org/obo/GO_0005575')
  );
});

it('flags a well-formed GO id that OLS cannot resolve as not found', async () => {
  mockValidate.mockResolvedValue(null);
  renderField({ id: 'GO:9999999' });
  expect(await screen.findByText(/id not found/i)).toBeInTheDocument();
});

it('shows the resolved label for a GO id that OLS resolves', async () => {
  mockValidate.mockResolvedValueOnce({ id: 'GO:0005840', label: 'ribosome', synonyms: [] });
  renderField({ id: 'GO:0005840' });
  expect(await screen.findByText(/ribosome · GO:0005840/i)).toBeInTheDocument();
});

it('fills the name from the picked term when the name is empty', async () => {
  mockSearch.mockResolvedValue([{ id: 'GO:0005840', label: 'ribosome', synonyms: [] }]);
  const { onChange } = renderField({ name: '', id: '' });
  fireEvent.mouseDown(screen.getByRole('combobox', { name: /Ontology/ }));
  fireEvent.click(screen.getByRole('option', { name: /^GO/ }));
  await userEvent.type(screen.getByLabelText(/Object ID/), 'ribo');
  fireEvent.click(await screen.findByRole('option', { name: /ribosome/i }));
  expect(onChange).toHaveBeenCalledWith({ object_id: 'GO:0005840', object_name: 'ribosome' });
});

it('keeps an existing name when a term is picked', async () => {
  mockSearch.mockResolvedValue([{ id: 'GO:0005840', label: 'ribosome', synonyms: [] }]);
  const { onChange } = renderField({ name: 'my object', id: '' });
  fireEvent.mouseDown(screen.getByRole('combobox', { name: /Ontology/ }));
  fireEvent.click(screen.getByRole('option', { name: /^GO/ }));
  await userEvent.type(screen.getByLabelText(/Object ID/), 'ribo');
  fireEvent.click(await screen.findByRole('option', { name: /ribosome/i }));
  expect(onChange).toHaveBeenCalledWith({ object_id: 'GO:0005840' });
});

it('re-sets the id when the same term is picked after editing the search text', async () => {
  mockSearch.mockResolvedValue([{ id: 'GO:0005840', label: 'ribosome', synonyms: [] }]);
  mockValidate.mockResolvedValue({ id: 'GO:0005840', label: 'ribosome', synonyms: [] });
  renderControlled({ object_name: 'x', object_id: '' });
  fireEvent.mouseDown(screen.getByRole('combobox', { name: /Ontology/ }));
  fireEvent.click(screen.getByRole('option', { name: /^GO/ }));
  const idInput = screen.getByLabelText(/Object ID/);

  await userEvent.type(idInput, 'ribo');
  fireEvent.click(await screen.findByRole('option', { name: /ribosome/i }));
  await screen.findByText(/ribosome · GO:0005840/i);

  await userEvent.type(idInput, 'z');
  fireEvent.click(await screen.findByRole('option', { name: /ribosome/i }));
  expect(await screen.findByText(/ribosome · GO:0005840/i)).toBeInTheDocument();
});

it('preserves a full CHEBI id typed character by character', async () => {
  renderControlled({ object_name: '', object_id: '' });
  fireEvent.mouseDown(screen.getByRole('combobox', { name: /Ontology/ }));
  fireEvent.click(screen.getByRole('option', { name: /^CHEBI/ }));
  const idInput = screen.getByLabelText(/Object ID/);
  await userEvent.type(idInput, 'CHEBI:12345');
  expect(idInput).toHaveValue('CHEBI:12345');
});
