import '@testing-library/jest-dom';
import { useState } from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

import { AnnotationMetadataForm } from './AnnotationMetadataForm';
import { searchOntology, validateOntologyId } from '../../services/ols';
import type { DepositionAnnotation } from '../../types';

jest.mock('../../services/ols', () => ({
  ...jest.requireActual('../../services/ols'),
  searchOntology: jest.fn().mockResolvedValue([]),
  validateOntologyId: jest.fn().mockResolvedValue(null),
}));

const mockSearch = searchOntology as jest.Mock;
const mockValidate = validateOntologyId as jest.Mock;
afterEach(() => jest.clearAllMocks());

const base: DepositionAnnotation = { copick_kind: 'picks', copick_ref: 'ribosome:relion/1' };

function setup(over: Partial<DepositionAnnotation> = {}, readOnly = false) {
  const onChange = jest.fn();
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={client}>
      <AnnotationMetadataForm annotation={{ ...base, ...over }} onChange={onChange} readOnly={readOnly} />
    </QueryClientProvider>
  );
  return { onChange };
}

function StatefulForm({ initial }: { initial: DepositionAnnotation }) {
  const [ann, setAnn] = useState(initial);
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return (
    <QueryClientProvider client={client}>
      <AnnotationMetadataForm annotation={ann} onChange={(p) => setAnn((a) => ({ ...a, ...p }))} />
    </QueryClientProvider>
  );
}

const expand = (title: RegExp) => fireEvent.click(screen.getByRole('button', { name: title }));

it('renders the object name in the always-open OBJECT block', () => {
  setup({ object_name: 'ribosome' });
  expect(screen.getByLabelText(/Object name/)).toHaveValue('ribosome');
});

it('emits a patch when the object name changes', () => {
  const { onChange } = setup();
  fireEvent.change(screen.getByLabelText(/Object name/), { target: { value: 'ribosome' } });
  expect(onChange).toHaveBeenCalledWith({ object_name: 'ribosome' });
});

it('edits object state after expanding Details', () => {
  const { onChange } = setup();
  expand(/Details/);
  fireEvent.change(screen.getByLabelText('Object state'), { target: { value: 'apo' } });
  expect(onChange).toHaveBeenCalledWith({ object_state: 'apo' });
});

it('toggles a boolean flag after expanding Details', () => {
  const { onChange } = setup();
  expand(/Details/);
  fireEvent.click(screen.getByLabelText(/Ground truth/));
  expect(onChange).toHaveBeenCalledWith({ ground_truth_status: true });
});

it('disables all inputs when readOnly', () => {
  setup({ object_name: 'x', ground_truth_status: true }, true);
  expect(screen.getByLabelText(/Object name/)).toBeDisabled();
  expect(screen.getByLabelText(/Ground truth/)).toBeDisabled();
});

it('shows the DOI count in the merged Details summary', () => {
  setup({ annotation_publication: '10.1/a, 10.2/b' });
  expect(screen.getByRole('button', { name: /Details/ })).toHaveTextContent('2 DOIs');
});

it('adds a method link with a default type (inside Method & links)', () => {
  const { onChange } = setup();
  expand(/Method & links/);
  fireEvent.click(screen.getByRole('button', { name: /add link/i }));
  expect(onChange).toHaveBeenCalledWith({ method_links: [{ link_type: 'source_code', link: '' }] });
});

it('edits an existing method link url', () => {
  const { onChange } = setup({ method_links: [{ id: 1, link_type: 'website', link: '' }] });
  fireEvent.change(screen.getByLabelText(/Link URL/), { target: { value: 'https://example.org' } });
  expect(onChange).toHaveBeenCalledWith({
    method_links: [{ id: 1, link_type: 'website', link: 'https://example.org' }],
  });
});

it('collapses Method & links and Details by default on an empty annotation', () => {
  setup();
  expect(screen.getByRole('button', { name: /Method & links/ })).toBeInTheDocument();
  expect(screen.getByRole('button', { name: /Details/ })).toBeInTheDocument();
  expect(screen.queryByLabelText('Annotation method')).not.toBeInTheDocument();
  expect(screen.queryByLabelText('Object state')).not.toBeInTheDocument();
});

it('auto-opens Details when a flag is already set (no click needed)', () => {
  setup({ ground_truth_status: true });
  expect(screen.getByLabelText(/Ground truth/)).toBeInTheDocument();
});

it('counts a method field in the Method & links summary', () => {
  setup({ annotation_method: 'TM' });
  expect(screen.getByRole('button', { name: /Method & links/ })).toHaveTextContent('1 of 2');
});

it('scopes GO object search to the cellular component branch (after picking GO)', async () => {
  setup();
  fireEvent.mouseDown(screen.getByRole('combobox', { name: /Ontology/ }));
  fireEvent.click(screen.getByRole('option', { name: /^GO/ }));
  await userEvent.type(screen.getByLabelText(/Object ID/), 'ribosome');
  await waitFor(() =>
    expect(mockSearch).toHaveBeenCalledWith('ribosome', 'go', 'http://purl.obolibrary.org/obo/GO_0005575')
  );
});

it('stores an EMDB object id as typed (manual reference type)', () => {
  const { onChange } = setup();
  fireEvent.mouseDown(screen.getByRole('combobox', { name: /Ontology/ }));
  fireEvent.click(screen.getByRole('option', { name: /^EMDB/ }));
  fireEvent.change(screen.getByLabelText(/Object ID/), { target: { value: 'EMD-1234' } });
  expect(onChange).toHaveBeenCalledWith({ object_id: 'EMD-1234' });
});

it('stores a PDB object id as typed (manual reference type)', () => {
  const { onChange } = setup();
  fireEvent.mouseDown(screen.getByRole('combobox', { name: /Ontology/ }));
  fireEvent.click(screen.getByRole('option', { name: /^PDB/ }));
  fireEvent.change(screen.getByLabelText(/Object ID/), { target: { value: 'PDB-4hhb' } });
  expect(onChange).toHaveBeenCalledWith({ object_id: 'PDB-4hhb' });
});

it('round-trips an existing EMD- object id to the EMDB type', () => {
  setup({ object_id: 'EMD-1234' });
  expect(screen.getByRole('combobox', { name: /Ontology/ })).toHaveTextContent('EMDB');
  expect(screen.getByLabelText(/Object ID/)).toHaveValue('EMD-1234');
});

it('gates the ID field until an ontology is chosen', () => {
  setup({ object_name: 'ribosome' });
  expect(screen.getByPlaceholderText('Choose an ontology first')).toBeDisabled();
});

it('accepts a pasted/typed accession in a searchable ontology', async () => {
  const { onChange } = setup();
  fireEvent.mouseDown(screen.getByRole('combobox', { name: /Ontology/ }));
  fireEvent.click(screen.getByRole('option', { name: /^GO/ }));
  await userEvent.type(screen.getByLabelText(/Object ID/), 'GO:0005840');
  expect(onChange).toHaveBeenCalledWith({ object_id: 'GO:0005840' });
});

it('does not flag the ontology as Required until the field is touched', () => {
  setup({ object_name: 'ribosome', object_id: '' });
  expect(screen.getByText(/choose the ontology this object belongs to/i).className).not.toMatch(/Mui-error/);
  fireEvent.blur(screen.getByRole('combobox', { name: /Ontology/ }));
  expect(screen.getByText(/choose the ontology this object belongs to/i).className).toMatch(/Mui-error/);
});

it('flags a well-formed GO id that OLS cannot resolve as not found', async () => {
  mockValidate.mockResolvedValue(null);
  setup({ object_id: 'GO:9999999' });
  expect(await screen.findByText(/id not found/i)).toBeInTheDocument();
});

it('shows the resolved label for a GO id that OLS resolves', async () => {
  mockValidate.mockResolvedValueOnce({ id: 'GO:0005840', label: 'ribosome', synonyms: [] });
  setup({ object_id: 'GO:0005840' });
  expect(await screen.findByText(/ribosome · GO:0005840/i)).toBeInTheDocument();
});

it('nudges review of a prefilled name that has no id yet', () => {
  setup({ object_name: 'ribosome', object_id: '' });
  expect(screen.getByText(/edit if needed/i)).toBeInTheDocument();
});

it('does not nudge in read-only mode', () => {
  setup({ object_name: 'ribosome', object_id: '' }, true);
  expect(screen.queryByText(/edit if needed/i)).not.toBeInTheDocument();
});

it('prompts to choose an ontology when none is set', () => {
  setup({ object_name: 'ribosome', object_id: '' });
  expect(screen.getByText(/choose the ontology this object belongs to/i)).toBeInTheDocument();
});

it('clears the object id when the ontology is changed', () => {
  const { onChange } = setup({ object_id: 'GO:0005840' });
  fireEvent.mouseDown(screen.getByRole('combobox', { name: /Ontology/ }));
  fireEvent.click(screen.getByRole('option', { name: /^UniProtKB/ }));
  expect(onChange).toHaveBeenCalledWith({ object_id: '' });
});

it('keeps the inferred ontology when an existing ID is cleared', async () => {
  render(<StatefulForm initial={{ ...base, object_id: 'GO:0005840', object_name: 'ribosome' }} />);
  await userEvent.clear(screen.getByLabelText(/Object ID/));
  // Keep the search field visible.
  expect(screen.queryByPlaceholderText('Choose an ontology first')).not.toBeInTheDocument();
  expect(screen.getByRole('combobox', { name: /Ontology/ })).toHaveTextContent('GO');
});

it('fills the name from the picked term when the name is empty', async () => {
  mockSearch.mockResolvedValue([{ id: 'GO:0005840', label: 'ribosome', synonyms: [] }]);
  const { onChange } = setup({ object_name: '', object_id: '' });
  fireEvent.mouseDown(screen.getByRole('combobox', { name: /Ontology/ }));
  fireEvent.click(screen.getByRole('option', { name: /^GO/ }));
  await userEvent.type(screen.getByLabelText(/Object ID/), 'ribo');
  fireEvent.click(await screen.findByRole('option', { name: /ribosome/i }));
  expect(onChange).toHaveBeenCalledWith({ object_id: 'GO:0005840', object_name: 'ribosome' });
});

it('keeps an existing name when a term is picked', async () => {
  mockSearch.mockResolvedValue([{ id: 'GO:0005840', label: 'ribosome', synonyms: [] }]);
  const { onChange } = setup({ object_name: 'my object', object_id: '' });
  fireEvent.mouseDown(screen.getByRole('combobox', { name: /Ontology/ }));
  fireEvent.click(screen.getByRole('option', { name: /^GO/ }));
  await userEvent.type(screen.getByLabelText(/Object ID/), 'ribo');
  fireEvent.click(await screen.findByRole('option', { name: /ribosome/i }));
  expect(onChange).toHaveBeenCalledWith({ object_id: 'GO:0005840' });
});

it('re-sets the id when the same term is picked after editing the search text', async () => {
  mockSearch.mockResolvedValue([{ id: 'GO:0005840', label: 'ribosome', synonyms: [] }]);
  mockValidate.mockResolvedValue({ id: 'GO:0005840', label: 'ribosome', synonyms: [] });
  render(<StatefulForm initial={{ ...base, object_name: 'x' }} />);
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
  render(<StatefulForm initial={base} />);
  fireEvent.mouseDown(screen.getByRole('combobox', { name: /Ontology/ }));
  fireEvent.click(screen.getByRole('option', { name: /^CHEBI/ }));
  const idInput = screen.getByLabelText(/Object ID/);
  await userEvent.type(idInput, 'CHEBI:12345');
  expect(idInput).toHaveValue('CHEBI:12345');
});

it('adopts the ontology when a rescan supplies the id after mount', () => {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const { rerender } = render(
    <QueryClientProvider client={client}>
      <AnnotationMetadataForm annotation={{ ...base, object_name: 'x' }} onChange={jest.fn()} />
    </QueryClientProvider>
  );
  expect(screen.getByPlaceholderText('Choose an ontology first')).toBeInTheDocument();
  rerender(
    <QueryClientProvider client={client}>
      <AnnotationMetadataForm
        annotation={{ ...base, object_name: 'x', object_id: 'GO:0005840' }}
        onChange={jest.fn()}
      />
    </QueryClientProvider>
  );
  expect(screen.queryByPlaceholderText('Choose an ontology first')).not.toBeInTheDocument();
  expect(screen.getByRole('combobox', { name: /Ontology/ })).toHaveTextContent('GO');
  expect(screen.getByLabelText(/Object ID/)).toHaveValue('GO:0005840');
});

it('flags an invalid manual EMDB id format', async () => {
  render(<StatefulForm initial={base} />);
  fireEvent.mouseDown(screen.getByRole('combobox', { name: /Ontology/ }));
  fireEvent.click(screen.getByRole('option', { name: /^EMDB/ }));
  fireEvent.change(screen.getByLabelText(/Object ID/), { target: { value: 'EMD-xx' } });
  expect(await screen.findByText(/expected format like EMD-1234/i)).toBeInTheDocument();
});

it('toggles the default-in-viewer flag after expanding Details', () => {
  const { onChange } = setup();
  expand(/Details/);
  fireEvent.click(screen.getByLabelText('Default in viewer'));
  expect(onChange).toHaveBeenCalledWith({ is_visualization_default: true });
});
