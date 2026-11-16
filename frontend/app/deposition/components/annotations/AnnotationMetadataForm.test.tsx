import '@testing-library/jest-dom';
import { useState } from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

import { AnnotationMetadataForm } from './AnnotationMetadataForm';
import type { DepositionAnnotation } from '../../types';

jest.mock('../../services/ols', () => ({
  ...jest.requireActual('../../services/ols'),
  searchOntology: jest.fn().mockResolvedValue([]),
  validateOntologyId: jest.fn().mockResolvedValue(null),
}));

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
  const [client] = useState(() => new QueryClient({ defaultOptions: { queries: { retry: false } } }));
  return (
    <QueryClientProvider client={client}>
      <AnnotationMetadataForm annotation={ann} onChange={(p) => setAnn((a) => ({ ...a, ...p }))} />
    </QueryClientProvider>
  );
}

const expand = (title: RegExp) => fireEvent.click(screen.getByRole('button', { name: title }));

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

it.each([
  ['Ground truth', 'ground_truth_status'],
  ['Default in viewer', 'is_visualization_default'],
])('toggles the %s flag after expanding Details', (label, key) => {
  const { onChange } = setup();
  expand(/Details/);
  fireEvent.click(screen.getByLabelText(new RegExp(label)));
  expect(onChange).toHaveBeenCalledWith({ [key]: true });
});

it('keeps read-only text selectable and disables editing controls', () => {
  setup({ object_name: 'x', ground_truth_status: true }, true);
  expect(screen.getByLabelText(/Object name/)).toHaveAttribute('readonly');
  expect(screen.getByLabelText(/Object name/)).not.toBeDisabled();
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

it('opens incomplete selected metadata and clears inline method errors as fields are filled', () => {
  render(<StatefulForm initial={{ ...base, is_selected: true }} />);
  const section = screen.getByRole('button', { name: /Method & links/ });
  expect(section).toHaveAttribute('aria-expanded', 'true');
  fireEvent.click(section);
  expect(section).toHaveAttribute('aria-expanded', 'false');
  fireEvent.click(section);
  const method = screen.getByLabelText(/Annotation method/);
  const software = screen.getByLabelText(/Annotation software/);
  expect(method).toBeRequired();
  expect(software).toBeRequired();
  expect(method).toHaveAttribute('aria-invalid', 'true');
  expect(software).toHaveAttribute('aria-invalid', 'true');
  expect(screen.getByText('Object ID is required; choose an ontology first.')).toBeInTheDocument();
  fireEvent.change(method, { target: { value: 'Manual picking' } });
  fireEvent.change(software, { target: { value: 'Copick' } });
  expect(method).toHaveAttribute('aria-invalid', 'false');
  expect(software).toHaveAttribute('aria-invalid', 'false');
});

it('auto-opens Details when a flag is already set (no click needed)', () => {
  setup({ ground_truth_status: true });
  expect(screen.getByLabelText(/Ground truth/)).toBeInTheDocument();
});

it('counts a method field in the Method & links summary', () => {
  setup({ annotation_method: 'TM' });
  expect(screen.getByRole('button', { name: /Method & links/ })).toHaveTextContent('1 of 2');
});

it.each([
  ['EMDB', 'EMD-1234'],
  ['PDB', 'PDB-4hhb'],
])('stores a manual %s object id as typed', (ontology, id) => {
  const { onChange } = setup();
  fireEvent.mouseDown(screen.getByRole('combobox', { name: /Ontology/ }));
  fireEvent.click(screen.getByRole('option', { name: new RegExp(`^${ontology}`) }));
  fireEvent.change(screen.getByLabelText(/Object ID/), { target: { value: id } });
  expect(onChange).toHaveBeenCalledWith({ object_id: id });
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

it('does not flag the ontology as Required until the field is touched', () => {
  setup({ object_name: 'ribosome', object_id: '' });
  expect(screen.getByText(/choose the ontology this object belongs to/i).className).not.toMatch(/Mui-error/);
  fireEvent.blur(screen.getByRole('combobox', { name: /Ontology/ }));
  expect(screen.getByText(/choose the ontology this object belongs to/i).className).toMatch(/Mui-error/);
});

it('nudges review of a prefilled name that has no id yet', () => {
  setup({ object_name: 'ribosome', object_id: '' });
  expect(screen.getByText(/edit if needed/i)).toBeInTheDocument();
});

it('does not nudge in read-only mode', () => {
  setup({ object_name: 'ribosome', object_id: '' }, true);
  expect(screen.queryByText(/edit if needed/i)).not.toBeInTheDocument();
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
