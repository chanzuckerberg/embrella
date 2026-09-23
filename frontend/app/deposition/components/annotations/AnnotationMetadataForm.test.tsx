import '@testing-library/jest-dom';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

import { AnnotationMetadataForm } from './AnnotationMetadataForm';
import { searchOntology } from '../../services/ols';
import type { DepositionAnnotation } from '../../types';

jest.mock('../../services/ols', () => ({
  ...jest.requireActual('../../services/ols'),
  searchOntology: jest.fn().mockResolvedValue([]),
  validateOntologyId: jest.fn().mockResolvedValue(null),
}));

const mockSearch = searchOntology as jest.Mock;
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

it('scopes GO object search to the cellular component branch', async () => {
  setup();
  fireEvent.change(screen.getByLabelText(/Object name/), { target: { value: 'ribosome' } });
  await waitFor(() =>
    expect(mockSearch).toHaveBeenCalledWith('ribosome', 'go', 'http://purl.obolibrary.org/obo/GO_0005575')
  );
});

it('stores an EMDB object id in EMD-#### form (hyphen separator)', () => {
  const { onChange } = setup();
  fireEvent.mouseDown(screen.getByRole('combobox', { name: 'Ontology' }));
  fireEvent.click(screen.getByRole('option', { name: 'EMDB' }));
  fireEvent.change(screen.getByLabelText(/Object ID/), { target: { value: '1234' } });
  expect(onChange).toHaveBeenCalledWith({ object_id: 'EMD-1234' });
});

it('stores a PDB object id in PDB-xxxx form (hyphen separator)', () => {
  const { onChange } = setup();
  fireEvent.mouseDown(screen.getByRole('combobox', { name: 'Ontology' }));
  fireEvent.click(screen.getByRole('option', { name: 'PDB' }));
  fireEvent.change(screen.getByLabelText(/Object ID/), { target: { value: '4hhb' } });
  expect(onChange).toHaveBeenCalledWith({ object_id: 'PDB-4hhb' });
});

it('round-trips an existing EMD- object id back to the EMDB type and bare value', () => {
  setup({ object_id: 'EMD-1234' });
  expect(screen.getByRole('combobox', { name: 'Ontology' })).toHaveTextContent('EMDB');
  expect(screen.getByLabelText(/Object ID/)).toHaveValue('1234');
});

it('warns when the object name is filled but no ontology id is selected', () => {
  setup({ object_name: 'ribosome', object_id: '' });
  expect(screen.getByText(/no ontology id/i)).toBeInTheDocument();
});

it('does not warn once the object has both a name and an id', () => {
  setup({ object_name: 'ribosome', object_id: 'GO:0005840' });
  expect(screen.queryByText(/no ontology id/i)).not.toBeInTheDocument();
});

it('does not warn in read-only mode', () => {
  setup({ object_name: 'ribosome', object_id: '' }, true);
  expect(screen.queryByText(/no ontology id/i)).not.toBeInTheDocument();
});

it('clears the object id when the ontology is changed', () => {
  const { onChange } = setup({ object_id: 'GO:0005840' });
  fireEvent.mouseDown(screen.getByRole('combobox', { name: 'Ontology' }));
  fireEvent.click(screen.getByRole('option', { name: 'UniProtKB' }));
  expect(onChange).toHaveBeenCalledWith({ object_id: '' });
});

it('toggles the default-in-viewer flag after expanding Details', () => {
  const { onChange } = setup();
  expand(/Details/);
  fireEvent.click(screen.getByLabelText('Default in viewer'));
  expect(onChange).toHaveBeenCalledWith({ is_visualization_default: true });
});
